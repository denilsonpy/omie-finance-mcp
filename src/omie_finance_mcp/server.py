"""MCP Server para integração com o OMIE ERP."""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

from .client import OmieClient
from .tools import (
    suppliers,
    accounts_payable,
    accounts_receivable,
    bank_transactions,
    bank_accounts,
    cash_flow,
    receivable_boletos,
    receivable_pix,
    financial_movements,
    finance_registries,
)

# Busca .env no diretório atual e em ~/.config/omie-mcp/ (útil para uso via uvx)
load_dotenv()
load_dotenv(os.path.expanduser("~/.config/omie-mcp/.env"))


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    # Só usado em modo stdio (um único usuário por processo). Em modo HTTP
    # multi-tenant, cada requisição traz suas próprias credenciais via HTTP
    # Basic Auth (ver auth.py) e este client nunca chega a ser usado —
    # por isso as env vars são opcionais aqui.
    app_key = os.environ.get("OMIE_APP_KEY")
    app_secret = os.environ.get("OMIE_APP_SECRET")
    client = OmieClient(app_key=app_key, app_secret=app_secret) if app_key and app_secret else None
    try:
        yield {"omie": client}
    finally:
        if client:
            await client.aclose()


mcp = FastMCP(
    name="omie-finance-mcp",
    instructions=(
        "Servidor MCP para controle financeiro no ERP OMIE. "
        "Permite gerenciar: fornecedores, contas a pagar, contas a receber, "
        "lançamentos bancários, contas correntes, fluxo de caixa, boletos, "
        "PIX, movimentos financeiros e cadastros auxiliares (bancos, DRE, "
        "tipos de documento, tipos de conta corrente, finalidade de "
        "transferência, origem de lançamento e bandeiras de cartão). "
        "Datas devem ser informadas no formato dd/mm/aaaa."
    ),
    lifespan=lifespan,
)

# Registra todas as ferramentas financeiras
suppliers.register(mcp)
accounts_payable.register(mcp)
accounts_receivable.register(mcp)
bank_transactions.register(mcp)
bank_accounts.register(mcp)
cash_flow.register(mcp)
receivable_boletos.register(mcp)
receivable_pix.register(mcp)
financial_movements.register(mcp)
finance_registries.register(mcp)


def main():
    # "stdio" (padrão) é usado por clientes que sobem este processo
    # diretamente (Claude Desktop via uvx) — um único usuário, credenciais
    # fixas no ambiente. "streamable-http" roda como serviço HTTP
    # persistente e multi-tenant (usado no Docker, ver docker-compose.yml):
    # cada cliente autentica com o próprio app_key/app_secret via HTTP Basic
    # Auth (ver auth.py), então precisamos injetar nosso próprio middleware
    # no app ASGI em vez de usar mcp.run() diretamente.
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
        return
    if transport != "streamable-http":
        raise ValueError(
            f"MCP_TRANSPORT={transport!r} não suportado. Use 'stdio' ou 'streamable-http'."
        )

    import anyio
    import uvicorn

    from .auth import BasicAuthMiddleware

    mcp.settings.host = os.environ.get("MCP_HOST", "0.0.0.0")
    mcp.settings.port = int(os.environ.get("MCP_PORT", "8020"))

    # Proteção anti-DNS-rebinding do próprio SDK do MCP: por padrão só aceita
    # Host/Origin de localhost. Atrás de um domínio público (reverse proxy,
    # IP direto, sslip.io, etc.), o hostname real que os clientes usam
    # precisa ser adicionado aqui — senão toda requisição externa recebe 421.
    extra_hosts = [h.strip() for h in os.environ.get("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    mcp.settings.transport_security.allowed_hosts = [
        "127.0.0.1:*", "localhost:*", "[::1]:*", *extra_hosts,
    ]
    extra_origins = [o.strip() for o in os.environ.get("MCP_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    mcp.settings.transport_security.allowed_origins = [
        "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*", *extra_origins,
    ]

    app = mcp.streamable_http_app()
    app.add_middleware(BasicAuthMiddleware)

    config = uvicorn.Config(
        app,
        host=mcp.settings.host,
        port=mcp.settings.port,
        log_level=mcp.settings.log_level.lower(),
    )
    anyio.run(uvicorn.Server(config).serve)


if __name__ == "__main__":
    main()
