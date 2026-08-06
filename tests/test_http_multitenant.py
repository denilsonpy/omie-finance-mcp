"""End-to-end do transporte streamable-http, contra um servidor de verdade
(sem rede: o OmieClient está substituído pelo FakeOmieClient).

O teste que importa aqui é `test_cada_cliente_usa_a_propria_credencial`: ele
trava a regressão que motivou esta camada. Resolver a credencial num
ContextVar setado pelo middleware passa nos testes de unidade e mesmo assim
erra em produção — no streamable-http o loop da sessão MCP roda numa task
criada durante o `initialize`, então o handler da tool enxerga o ContextVar
congelado naquela primeira requisição. Só um teste com dois clientes
diferentes na mesma instância do servidor pega isso.
"""

import json

import anyio
import httpx
from mcp.client.session import ClientSession

# `streamablehttp_client` está deprecado a partir do mcp 1.27 em favor de
# `streamable_http_client`, que recebe um httpx.AsyncClient em vez de headers.
# Ficamos no antigo enquanto o piso da dependência for mcp>=1.26 (o aviso está
# silenciado em pyproject.toml).
from mcp.client.streamable_http import streamablehttp_client as streamable_http_client

from omie_finance_mcp.auth import APP_KEY_HEADER, APP_SECRET_HEADER

from .conftest import basic_header

CLIENTE_A = ("1111111111111", "segredo-do-cliente-a")
CLIENTE_B = ("2222222222222", "segredo-do-cliente-b")


async def _listar_contas(base_url: str, headers: dict[str, str]) -> dict:
    async with streamable_http_client(f"{base_url}/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("listar_contas_correntes", {})
            return json.loads(result.content[0].text)


def test_cada_cliente_usa_a_propria_credencial(http_server):
    async def run():
        a = await _listar_contas(http_server, {"Authorization": basic_header(*CLIENTE_A)})
        b = await _listar_contas(
            http_server,
            {APP_KEY_HEADER: CLIENTE_B[0], APP_SECRET_HEADER: CLIENTE_B[1]},
        )
        return a, b

    a, b = anyio.run(run)

    assert a["app_key_usada"] == CLIENTE_A[0]
    assert a["app_secret_usado"] == CLIENTE_A[1]
    assert b["app_key_usada"] == CLIENTE_B[0]
    assert b["app_secret_usado"] == CLIENTE_B[1]
    # Nenhum dos dois caiu na credencial do ambiente do servidor.
    assert "app-key-do-servidor" not in (a["app_key_usada"], b["app_key_usada"])


def test_varias_chamadas_na_mesma_sessao_mantem_a_credencial(http_server):
    """A credencial precisa valer para toda chamada da sessão, não só a primeira."""

    async def run():
        headers = {"Authorization": basic_header(*CLIENTE_A)}
        async with streamable_http_client(f"{http_server}/mcp", headers=headers) as (rd, wr, _):
            async with ClientSession(rd, wr) as session:
                await session.initialize()
                resultados = []
                for _ in range(3):
                    result = await session.call_tool("listar_contas_correntes", {})
                    resultados.append(json.loads(result.content[0].text)["app_key_usada"])
                return resultados

    assert anyio.run(run) == [CLIENTE_A[0]] * 3


def test_requisicao_sem_credencial_recebe_401(http_server):
    async def run():
        async with httpx.AsyncClient() as http:
            return await http.post(
                f"{http_server}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                headers={"Accept": "application/json, text/event-stream"},
            )

    response = anyio.run(run)
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
    assert "www-authenticate" not in response.headers


def test_credencial_mal_formada_recebe_401(http_server):
    async def run():
        async with httpx.AsyncClient() as http:
            return await http.post(
                f"{http_server}/mcp",
                json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Authorization": "Basic isto-nao-e-base64!!",
                },
            )

    assert anyio.run(run).status_code == 401
