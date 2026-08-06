"""Testes da autenticação: extração da credencial, middleware, cache e
resolução por chamada. Nenhum deles sai na rede."""

import json

import anyio
import pytest

from omie_finance_mcp import auth
from omie_finance_mcp.auth import (
    APP_KEY_HEADER,
    APP_SECRET_HEADER,
    OmieAuthMiddleware,
    OmieCredentials,
    credentials_from_request,
    credentials_from_scope,
    get_current_client,
)

from .conftest import basic_header, fake_context, fake_request, http_scope

APP_KEY = "1234567890123"
APP_SECRET = "aaaabbbbccccddddeeeeffff00001111"


# ----------------------------------------------------------------------
# Extração da credencial
# ----------------------------------------------------------------------


def test_basic_auth_no_scope():
    scope = http_scope({"Authorization": basic_header(APP_KEY, APP_SECRET)})
    assert credentials_from_scope(scope) == OmieCredentials(APP_KEY, APP_SECRET)


def test_headers_proprios_no_scope():
    scope = http_scope({APP_KEY_HEADER: APP_KEY, APP_SECRET_HEADER: APP_SECRET})
    assert credentials_from_scope(scope) == OmieCredentials(APP_KEY, APP_SECRET)


def test_basic_auth_no_request():
    request = fake_request({"authorization": basic_header(APP_KEY, APP_SECRET)})
    assert credentials_from_request(request) == OmieCredentials(APP_KEY, APP_SECRET)


def test_headers_proprios_no_request_sao_case_insensitive():
    request = fake_request({"x-OMIE-app-KEY": APP_KEY, "X-omie-App-Secret": APP_SECRET})
    assert credentials_from_request(request) == OmieCredentials(APP_KEY, APP_SECRET)


def test_basic_invalido_cai_para_os_headers_proprios():
    scope = http_scope(
        {
            "Authorization": "Basic nao-e-base64!!",
            APP_KEY_HEADER: APP_KEY,
            APP_SECRET_HEADER: APP_SECRET,
        }
    )
    assert credentials_from_scope(scope) == OmieCredentials(APP_KEY, APP_SECRET)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic nao-e-base64!!"},
        {"Authorization": f"Bearer {APP_KEY}:{APP_SECRET}"},
        {"Authorization": basic_header(APP_KEY, "")},
        {"Authorization": basic_header("", APP_SECRET)},
        # base64 válido, mas sem os dois pontos separando chave e segredo
        {"Authorization": "Basic c2Vtc2VwYXJhZG9y"},
        {APP_KEY_HEADER: APP_KEY},
        {APP_SECRET_HEADER: APP_SECRET},
        {APP_KEY_HEADER: "   ", APP_SECRET_HEADER: APP_SECRET},
    ],
    ids=[
        "sem-headers",
        "basic-nao-base64",
        "bearer-nao-e-aceito",
        "segredo-vazio",
        "chave-vazia",
        "sem-separador",
        "so-a-chave",
        "so-o-segredo",
        "chave-em-branco",
    ],
)
def test_credenciais_ausentes_ou_mal_formadas(headers):
    assert credentials_from_scope(http_scope(headers)) is None


# ----------------------------------------------------------------------
# Middleware
# ----------------------------------------------------------------------


class RecordingApp:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def __call__(self, scope, receive, send) -> None:
        self.calls.append(scope)
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


async def _drive(middleware, scope) -> list[dict]:
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    await middleware(scope, receive, send)
    return sent


def test_requisicao_com_credencial_passa():
    downstream = RecordingApp()
    sent = anyio.run(
        _drive,
        OmieAuthMiddleware(downstream),
        http_scope({"Authorization": basic_header(APP_KEY, APP_SECRET)}),
    )
    assert len(downstream.calls) == 1
    assert sent[0]["status"] == 200


def test_requisicao_sem_credencial_recebe_401_e_nao_chega_no_app():
    downstream = RecordingApp()
    sent = anyio.run(_drive, OmieAuthMiddleware(downstream), http_scope({}))

    assert downstream.calls == []
    start = sent[0]
    assert start["status"] == 401
    # Sem desafio WWW-Authenticate: ele faria cliente MCP tentar um fluxo
    # OAuth contra um authorization server que não existe aqui.
    assert not any(name == b"www-authenticate" for name, _ in start["headers"])

    body = json.loads(sent[1]["body"])
    assert body["error"] == "unauthorized"
    assert APP_KEY_HEADER in body["message"]


def test_preflight_options_passa_sem_credencial():
    downstream = RecordingApp()
    anyio.run(_drive, OmieAuthMiddleware(downstream), http_scope({}, method="OPTIONS"))
    assert len(downstream.calls) == 1


def test_lifespan_passa_sem_credencial():
    """É o lifespan do app streamable-http que sobe o session manager do MCP."""
    downstream_calls: list[dict] = []

    async def downstream(scope, receive, send):
        downstream_calls.append(scope)

    async def run():
        await OmieAuthMiddleware(downstream)({"type": "lifespan"}, None, None)

    anyio.run(run)
    assert len(downstream_calls) == 1


# ----------------------------------------------------------------------
# Cache de clients
# ----------------------------------------------------------------------


def test_mesma_credencial_reaproveita_o_client():
    first = auth._client_for(OmieCredentials(APP_KEY, APP_SECRET))
    second = auth._client_for(OmieCredentials(APP_KEY, APP_SECRET))
    assert first is second


def test_credenciais_diferentes_nao_compartilham_client():
    first = auth._client_for(OmieCredentials(APP_KEY, APP_SECRET))
    second = auth._client_for(OmieCredentials("9999999999999", "outro-segredo"))
    assert first is not second
    assert second.app_key == "9999999999999"


def test_segredo_rotacionado_troca_o_client_e_fecha_o_antigo():
    async def run():
        antigo = auth._client_for(OmieCredentials(APP_KEY, APP_SECRET))
        novo = auth._client_for(OmieCredentials(APP_KEY, "segredo-rotacionado"))
        assert novo is not antigo
        assert novo.app_secret == "segredo-rotacionado"
        # O fechamento do client substituído é agendado no event loop.
        await anyio.sleep(0)
        return antigo

    antigo = anyio.run(run)
    assert antigo.closed


def test_aclose_all_fecha_e_esvazia_o_cache():
    async def run():
        client = auth._client_for(OmieCredentials(APP_KEY, APP_SECRET))
        await auth.aclose_all()
        return client

    client = anyio.run(run)
    assert client.closed
    assert auth._clients_by_app_key == {}


# ----------------------------------------------------------------------
# Resolução por chamada
# ----------------------------------------------------------------------


def test_client_vem_da_credencial_da_requisicao():
    ctx = fake_context(request=fake_request({"authorization": basic_header(APP_KEY, APP_SECRET)}))
    client = get_current_client(ctx)
    assert client.app_key == APP_KEY
    assert client.app_secret == APP_SECRET


def test_requisicao_ignora_a_credencial_do_lifespan():
    """O client do ambiente não pode atender uma requisição HTTP: seria operar
    numa conta OMIE que não é a de quem chamou."""
    do_servidor = object()
    ctx = fake_context(
        request=fake_request({"authorization": basic_header(APP_KEY, APP_SECRET)}),
        lifespan_context={"omie": do_servidor},
    )
    assert get_current_client(ctx) is not do_servidor


def test_requisicao_sem_credencial_falha_mesmo_com_client_no_lifespan():
    ctx = fake_context(request=fake_request({}), lifespan_context={"omie": object()})
    with pytest.raises(RuntimeError, match="sem credencial"):
        get_current_client(ctx)


def test_sem_requisicao_usa_o_client_do_lifespan():
    """Modo stdio: não existe requisição HTTP."""
    do_servidor = object()
    ctx = fake_context(lifespan_context={"omie": do_servidor})
    assert get_current_client(ctx) is do_servidor


def test_sem_requisicao_e_sem_client_explica_o_que_falta():
    ctx = fake_context(lifespan_context={"omie": None})
    with pytest.raises(RuntimeError, match="OMIE_APP_KEY"):
        get_current_client(ctx)
