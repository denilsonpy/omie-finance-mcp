import base64
import socket
import threading
from types import SimpleNamespace

import anyio
import pytest
import uvicorn

from omie_finance_mcp import auth


class FakeOmieClient:
    """Substitui o OmieClient nos testes: registra a credencial recebida e
    nunca fala com a API do OMIE."""

    def __init__(self, app_key: str, app_secret: str) -> None:
        self.app_key = app_key
        self.app_secret = app_secret
        self.closed = False

    async def listar_contas_correntes(self, pagina: int = 1, registros_por_pagina: int = 20) -> dict:
        return {"app_key_usada": self.app_key, "app_secret_usado": self.app_secret}

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def fake_omie_client(monkeypatch):
    """Nenhum teste deve construir um OmieClient de verdade nem sair na rede."""
    monkeypatch.setattr(auth, "OmieClient", FakeOmieClient)
    auth._clients_by_app_key.clear()
    yield FakeOmieClient
    auth._clients_by_app_key.clear()


def basic_header(app_key: str, app_secret: str) -> str:
    encoded = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()
    return f"Basic {encoded}"


def http_scope(headers: dict[str, str] | None = None, method: str = "POST", path: str = "/mcp") -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "client": ("203.0.113.7", 54321),
        "headers": [
            (name.lower().encode(), value.encode()) for name, value in (headers or {}).items()
        ],
    }


def fake_context(request=None, lifespan_context=None) -> SimpleNamespace:
    """Context do FastMCP reduzido ao que get_current_client() consulta."""
    return SimpleNamespace(
        request_context=SimpleNamespace(request=request, lifespan_context=lifespan_context)
    )


def fake_request(headers: dict[str, str]):
    from starlette.datastructures import Headers

    return SimpleNamespace(headers=Headers(headers))


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def http_server():
    """Servidor HTTP real numa thread, compartilhado por todos os testes.

    Uma única instância porque o session manager do streamable-http aceita um
    `run()` por instância, e o app do FastMCP fica em cache no módulo.

    OMIE_APP_KEY/OMIE_APP_SECRET vão preenchidos de propósito: é o cenário
    perigoso — se a resolução por requisição falhar, a credencial do servidor
    está ali para o código cair nela silenciosamente, e é isso que os testes
    de multi-tenant detectam.
    """
    from omie_finance_mcp import server
    from omie_finance_mcp.config import Settings

    port = _free_port()
    settings = Settings(
        omie_app_key="app-key-do-servidor",
        omie_app_secret="app-secret-do-servidor",
        mcp_transport="streamable-http",
        mcp_host="127.0.0.1",
        mcp_port=port,
        mcp_allowed_hosts="",
        mcp_allowed_origins="",
    )

    originais = (auth.OmieClient, server.OmieClient, server.get_settings)
    auth.OmieClient = FakeOmieClient
    server.OmieClient = FakeOmieClient
    server.get_settings = lambda: settings

    uvicorn_server = uvicorn.Server(
        uvicorn.Config(server.http_app(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=uvicorn_server.run, daemon=True)
    thread.start()

    async def wait_until_up():
        for _ in range(100):
            if uvicorn_server.started:
                return
            await anyio.sleep(0.05)
        raise RuntimeError("o servidor HTTP não subiu")

    anyio.run(wait_until_up)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        uvicorn_server.should_exit = True
        thread.join(timeout=10)
        auth.OmieClient, server.OmieClient, server.get_settings = originais
        auth._clients_by_app_key.clear()
