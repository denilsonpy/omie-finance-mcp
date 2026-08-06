"""MCP Server para integração com o OMIE ERP."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from . import auth
from .client import OmieClient
from .config import Settings, get_settings, parse_csv
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

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    # Este client só é usado em modo stdio (um único usuário por processo). Em
    # modo HTTP multi-tenant, cada requisição traz suas próprias credenciais
    # (ver auth.py) e ele nunca chega a ser usado — por isso as credenciais
    # são opcionais aqui.
    settings = get_settings()
    client = (
        OmieClient(app_key=settings.omie_app_key, app_secret=settings.omie_app_secret)
        if settings.omie_app_key and settings.omie_app_secret
        else None
    )
    try:
        yield {"omie": client}
    finally:
        if client is not None:
            await client.aclose()
        # Em modo HTTP, os clients por credencial ficam num cache no auth.py.
        await auth.aclose_all()


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


def _transport_security(settings: Settings) -> TransportSecuritySettings:
    """Monta a allowlist de Host/Origin do SDK a partir de MCP_ALLOWED_HOSTS.

    Vazio -> checagem desligada. Ela protege navegador contra DNS rebinding,
    que a exigência de credencial já barra (uma página que "rebindou" não tem
    a app_key/app_secret de ninguém), e deixar o padrão localhost do SDK no
    lugar torna todo cliente remoto inutilizável. Preencha os hosts para
    ligá-la de volta.
    """
    hosts = parse_csv(settings.mcp_allowed_hosts)
    extra_origins = parse_csv(settings.mcp_allowed_origins)
    if not hosts:
        if extra_origins:
            logger.warning(
                "MCP_ALLOWED_ORIGINS está preenchido mas MCP_ALLOWED_HOSTS não: "
                "é MCP_ALLOWED_HOSTS que liga a checagem, então os origins serão "
                "ignorados."
            )
        logger.info(
            "MCP_ALLOWED_HOSTS vazio: validação de Host desligada, qualquer Host é "
            "aceito (quem controla acesso é a credencial do OMIE). Preencha para "
            "ligar a checagem."
        )
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    # Host sem porta vale para qualquer porta: os clientes chegam pela porta
    # que o proxy da frente publica, que não é necessariamente MCP_PORT.
    allowed_hosts = [host if ":" in host else f"{host}:*" for host in hosts]
    allowed_hosts += ["127.0.0.1:*", "localhost:*", "[::1]:*"]
    allowed_origins = [
        f"{scheme}://{host}" for host in allowed_hosts for scheme in ("http", "https")
    ]
    allowed_origins += extra_origins
    logger.info("Validação de Host ligada para: %s", ", ".join(allowed_hosts))
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=allowed_origins,
    )


def http_app(settings: Settings):
    """App ASGI do transporte streamable-http, já atrás da exigência de credencial.

    Não é `mcp.run()`: o FastMCP monta o app Starlette internamente e não
    expõe hook para embrulhá-lo, e é justamente esse embrulho que garante que
    nenhuma requisição sem credencial chegue ao session manager do MCP.
    """
    mcp.settings.host = settings.mcp_host
    mcp.settings.port = settings.mcp_port
    # Precisa ser definido antes de montar o app: `streamable_http_app()`
    # entrega isto ao session manager e o mantém em cache. O FastMCP decidiu
    # no construtor, a partir do host padrão dele (127.0.0.1), ligar uma
    # allowlist só-localhost — e aí todo cliente remoto recebe 421 "Invalid
    # Host header" por mais válida que seja a credencial.
    mcp.settings.transport_security = _transport_security(settings)
    return auth.OmieAuthMiddleware(mcp.streamable_http_app())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.mcp_transport == "stdio":
        mcp.run(transport="stdio")
        return

    import uvicorn

    logger.info(
        "Transporte %s: cada cliente autentica com o próprio app_key/app_secret do OMIE",
        settings.mcp_transport,
    )
    uvicorn.run(
        http_app(settings),
        host=settings.mcp_host,
        port=settings.mcp_port,
        log_level=mcp.settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
