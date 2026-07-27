"""Resolve qual OmieClient atende a requisição atual, em modo multi-tenant HTTP.

Cada cliente se autentica com o próprio app_key/app_secret do OMIE via HTTP
Basic Auth (usuário = app_key, senha = app_secret). A própria API do OMIE é
quem valida se essas credenciais são reais — não existe aqui um cadastro
paralelo de credenciais para manter sincronizado, e um cliente jamais
consegue montar um OmieClient com a chave de outro.

Em modo stdio (uso local via uvx/Claude Desktop, um único usuário por
processo), nada disto entra em ação: o client vem do lifespan_context, como
sempre foi — ver get_current_client().
"""

from __future__ import annotations

import base64
import binascii
from contextlib import suppress
from contextvars import ContextVar

from mcp.server.fastmcp import Context
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from .client import OmieClient

_current_client: ContextVar["OmieClient | None"] = ContextVar("omie_client", default=None)

# Um OmieClient por app_key, reaproveitado entre requisições do mesmo cliente
# em vez de recriar o pool de conexões httpx a cada chamada.
_clients_by_app_key: dict[str, OmieClient] = {}


def get_current_client(ctx: Context) -> OmieClient:
    """Client OMIE da requisição atual.

    Em modo HTTP multi-tenant, vem das credenciais Basic Auth da requisição
    (ver BasicAuthMiddleware). Em modo stdio, cai para o client único do
    lifespan_context (OMIE_APP_KEY/OMIE_APP_SECRET do ambiente).
    """
    per_request = _current_client.get()
    if per_request is not None:
        return per_request

    client = ctx.request_context.lifespan_context.get("omie")
    if client is None:
        raise RuntimeError(
            "Nenhuma credencial OMIE disponível para esta chamada. "
            "Em modo HTTP, autentique com HTTP Basic Auth (app_key como "
            "usuário, app_secret como senha). Em modo stdio, defina "
            "OMIE_APP_KEY e OMIE_APP_SECRET no ambiente."
        )
    return client


def _client_for(app_key: str, app_secret: str) -> OmieClient:
    cached = _clients_by_app_key.get(app_key)
    if cached is None or cached.app_secret != app_secret:
        cached = OmieClient(app_key=app_key, app_secret=app_secret)
        _clients_by_app_key[app_key] = cached
    return cached


def _decode_basic_auth(header_value: str) -> tuple[str, str] | None:
    if not header_value.startswith("Basic "):
        return None
    with suppress(binascii.Error, UnicodeDecodeError, ValueError):
        decoded = base64.b64decode(header_value[len("Basic ") :]).decode("utf-8")
        app_key, _, app_secret = decoded.partition(":")
        if app_key and app_secret:
            return app_key, app_secret
    return None


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Exige HTTP Basic Auth (app_key/app_secret) em toda requisição e
    disponibiliza o OmieClient correspondente para get_current_client()
    durante o processamento dessa requisição."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        credentials = _decode_basic_auth(request.headers.get("authorization", ""))
        if credentials is None:
            return Response(
                "Autenticação necessária: HTTP Basic Auth com app_key como "
                "usuário e app_secret como senha do OMIE.",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="omie-mcp"'},
            )

        app_key, app_secret = credentials
        token = _current_client.set(_client_for(app_key, app_secret))
        try:
            return await call_next(request)
        finally:
            _current_client.reset(token)
