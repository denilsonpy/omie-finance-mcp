"""Autenticação das requisições e resolução do OmieClient de cada chamada.

Cada cliente se autentica com o próprio app_key/app_secret do OMIE, enviados
de uma destas duas formas:

    Authorization: Basic base64("app_key:app_secret")
    X-Omie-App-Key: <app_key>  +  X-Omie-App-Secret: <app_secret>

Quem valida se a credencial é real é a própria API do OMIE. Não existe aqui um
cadastro paralelo de credenciais para manter sincronizado, e um cliente jamais
consegue montar um OmieClient com a chave de outro.

São duas camadas, com responsabilidades deliberadamente separadas:

  - `OmieAuthMiddleware`, na borda ASGI, recusa com 401 toda requisição HTTP
    sem credencial — antes de ela chegar ao session manager do MCP.
  - `get_current_client()` resolve, a cada chamada de tool, qual OmieClient
    atende aquela chamada, a partir dos headers da requisição que a originou.

Por que a resolução acontece na chamada e não num ContextVar setado pelo
middleware: no transporte streamable-http o loop da sessão MCP roda numa task
criada durante o `initialize`, e uma task herda o contexto de quem a criou.
Um ContextVar setado pelo middleware chega ao handler congelado no valor
daquela primeira requisição, nunca no da requisição corrente. O que de fato
acompanha a requisição atual é `ctx.request_context.request`, que o SDK
injeta via `ServerMessageMetadata`.

Em modo stdio (uvx/Claude Desktop, um único usuário por processo) não existe
requisição HTTP: o client vem do `lifespan_context`, montado com
OMIE_APP_KEY/OMIE_APP_SECRET do ambiente.

O que esta camada NÃO oferece:
  - Confidencialidade. A credencial viaja em claro sobre HTTP simples; ponha
    um proxy com TLS na frente antes de expor isto fora de uma rede
    confiável.
  - Autorização. Quem apresenta uma credencial válida do OMIE pode chamar
    toda tool, exclusões incluídas, dentro do que aquela credencial permite
    no OMIE. Escopo por credencial (ex: uma chave somente-leitura) seria uma
    camada separada em cima desta.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hmac
import json
import logging
from contextlib import suppress
from typing import Any, NamedTuple

from mcp.server.fastmcp import Context

from .client import OmieClient

logger = logging.getLogger(__name__)

APP_KEY_HEADER = "X-Omie-App-Key"
APP_SECRET_HEADER = "X-Omie-App-Secret"

_BASIC_PREFIX = "basic "
_AUTHORIZATION_BYTES = b"authorization"
_APP_KEY_BYTES = APP_KEY_HEADER.lower().encode()
_APP_SECRET_BYTES = APP_SECRET_HEADER.lower().encode()

_UNAUTHORIZED_BODY = json.dumps(
    {
        "error": "unauthorized",
        "message": (
            "Credencial do OMIE ausente ou mal formada. Envie "
            "'Authorization: Basic base64(app_key:app_secret)' ou os headers "
            f"'{APP_KEY_HEADER}' e '{APP_SECRET_HEADER}'."
        ),
    },
    ensure_ascii=False,
).encode()


class OmieCredentials(NamedTuple):
    app_key: str
    app_secret: str


# Um OmieClient por app_key, reaproveitado entre requisições do mesmo cliente
# em vez de recriar o pool de conexões do httpx a cada chamada. O número de
# entradas é o número de credenciais distintas em uso, não o de requisições.
_clients_by_app_key: dict[str, OmieClient] = {}

# Fechamentos em andamento de clients substituídos. Guardados numa referência
# forte porque uma task solta pode ser coletada antes de terminar.
_pending_closes: set[asyncio.Task] = set()


# ----------------------------------------------------------------------
# Extração da credencial
# ----------------------------------------------------------------------


def _credentials_from_parts(
    authorization: str | None,
    app_key: str | None,
    app_secret: str | None,
) -> OmieCredentials | None:
    """Monta a credencial a partir dos três headers relevantes, se der."""
    if authorization:
        candidate = authorization.strip()
        if candidate.lower().startswith(_BASIC_PREFIX):
            decoded = _decode_basic(candidate)
            if decoded is not None:
                return decoded
    if app_key and app_key.strip() and app_secret and app_secret.strip():
        return OmieCredentials(app_key.strip(), app_secret.strip())
    return None


def _decode_basic(header_value: str) -> OmieCredentials | None:
    encoded = header_value[len(_BASIC_PREFIX) :].strip()
    with suppress(binascii.Error, UnicodeDecodeError, ValueError):
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        app_key, separator, app_secret = decoded.partition(":")
        if separator and app_key and app_secret:
            return OmieCredentials(app_key, app_secret)
    return None


def credentials_from_scope(scope: dict[str, Any]) -> OmieCredentials | None:
    """Credencial de um scope ASGI (usado pelo middleware, antes do Starlette)."""
    authorization = app_key = app_secret = None
    for name, value in scope.get("headers", ()):
        lowered = name.lower()
        if lowered == _AUTHORIZATION_BYTES:
            authorization = value.decode("latin-1")
        elif lowered == _APP_KEY_BYTES:
            app_key = value.decode("latin-1")
        elif lowered == _APP_SECRET_BYTES:
            app_secret = value.decode("latin-1")
    return _credentials_from_parts(authorization, app_key, app_secret)


def credentials_from_request(request: Any) -> OmieCredentials | None:
    """Credencial de um Request do Starlette (usado na chamada da tool)."""
    headers = getattr(request, "headers", None)
    if headers is None:
        return None
    return _credentials_from_parts(
        headers.get("authorization"),
        headers.get(APP_KEY_HEADER),
        headers.get(APP_SECRET_HEADER),
    )


# ----------------------------------------------------------------------
# Cache de clients
# ----------------------------------------------------------------------


def _same_secret(cached: OmieClient, presented: str) -> bool:
    # Tempo constante para a comparação não revelar, pelo tempo de resposta,
    # o quanto o segredo apresentado se aproxima do que está em cache.
    return hmac.compare_digest(cached.app_secret.encode(), presented.encode())


def _client_for(credentials: OmieCredentials) -> OmieClient:
    cached = _clients_by_app_key.get(credentials.app_key)
    if cached is not None and _same_secret(cached, credentials.app_secret):
        return cached

    client = OmieClient(app_key=credentials.app_key, app_secret=credentials.app_secret)
    _clients_by_app_key[credentials.app_key] = client
    if cached is not None:
        # Segredo rotacionado para a mesma app_key: sem isto o pool de
        # conexões do client antigo ficaria aberto até o processo morrer.
        _close_later(cached)
    return client


def _close_later(client: OmieClient) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # Fora de um event loop não há como fechar; acontece só em teste.
        return
    task = loop.create_task(client.aclose())
    _pending_closes.add(task)
    task.add_done_callback(_pending_closes.discard)


async def aclose_all() -> None:
    """Fecha todos os clients em cache. Chamado no shutdown do servidor."""
    clients = list(_clients_by_app_key.values())
    _clients_by_app_key.clear()
    for client in clients:
        with suppress(Exception):
            await client.aclose()


# ----------------------------------------------------------------------
# Resolução por chamada
# ----------------------------------------------------------------------


def get_current_client(ctx: Context) -> OmieClient:
    """OmieClient que atende a chamada de tool em curso.

    Em modo HTTP, montado com as credenciais da requisição que originou esta
    chamada. Em modo stdio, o client único do `lifespan_context`.
    """
    request = getattr(ctx.request_context, "request", None)
    if request is not None:
        credentials = credentials_from_request(request)
        if credentials is None:
            # OmieAuthMiddleware deveria ter recusado esta requisição com 401.
            # Chegando aqui, falhar é melhor que cair na credencial do
            # ambiente: seria operar numa conta OMIE que não é a de quem
            # chamou.
            raise RuntimeError(
                "Requisição HTTP sem credencial do OMIE chegou até a tool. "
                "Autentique com 'Authorization: Basic base64(app_key:app_secret)' "
                f"ou com os headers '{APP_KEY_HEADER}' e '{APP_SECRET_HEADER}'."
            )
        return _client_for(credentials)

    lifespan_context = getattr(ctx.request_context, "lifespan_context", None)
    client = lifespan_context.get("omie") if lifespan_context else None
    if client is None:
        raise RuntimeError(
            "Nenhuma credencial OMIE disponível para esta chamada. Em modo "
            "stdio, defina OMIE_APP_KEY e OMIE_APP_SECRET no ambiente."
        )
    return client


# ----------------------------------------------------------------------
# Middleware ASGI
# ----------------------------------------------------------------------


class OmieAuthMiddleware:
    """Embrulha um app ASGI recusando requisições HTTP sem credencial do OMIE.

    ASGI puro, e não `BaseHTTPMiddleware`: este app serve respostas SSE de
    longa duração, e o `BaseHTTPMiddleware` as intermedia por um par de
    streams próprio, mudando o comportamento de cancelamento e de
    contrapressão de algo que só precisa ser inspecionado no header.

    A resposta 401 sai sem `WWW-Authenticate` de propósito: um desafio
    `Basic` faz navegador e alguns clientes MCP abrirem prompt de senha ou
    tentarem um fluxo OAuth contra um authorization server que não existe
    aqui, transformando "credencial errada" numa falha confusa. O corpo JSON
    diz o que faltou.
    """

    def __init__(self, app) -> None:
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        # Lifespan (e websocket) não é requisição de cliente e não tem header
        # para autenticar — e é o lifespan do app streamable-http que sobe o
        # session manager do MCP, então precisa passar.
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        # Preflight de CORS não carrega credencial, por definição.
        if scope.get("method") == "OPTIONS" or credentials_from_scope(scope) is not None:
            await self._app(scope, receive, send)
            return

        client = scope.get("client")
        logger.warning(
            "Requisição sem credencial do OMIE recusada em %s (origem: %s)",
            scope.get("path", "?"),
            client[0] if client else "desconhecida",
        )
        await self._send_unauthorized(send)

    @staticmethod
    async def _send_unauthorized(send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(_UNAUTHORIZED_BODY)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": _UNAUTHORIZED_BODY})
