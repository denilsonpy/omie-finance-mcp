"""Tools de Boletos de Contas a Receber — endpoint: /financas/contareceberboleto/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def gerar_boleto(
        ctx: Context,
        codigo_titulo: Annotated[Optional[int], "Código do título no OMIE"] = None,
        codigo_titulo_integracao: Annotated[Optional[str], "Código de integração do título"] = None,
    ) -> dict:
        """Gera o boleto de um título de contas a receber já existente."""
        client = get_current_client(ctx)
        return await client.gerar_boleto(
            codigo_titulo=codigo_titulo,
            codigo_titulo_integracao=codigo_titulo_integracao,
        )

    @mcp.tool()
    async def obter_boleto(
        ctx: Context,
        codigo_titulo: Annotated[Optional[int], "Código do título no OMIE"] = None,
        codigo_titulo_integracao: Annotated[Optional[str], "Código de integração do título"] = None,
    ) -> dict:
        """Obtém o link de download do boleto de um título já gerado."""
        client = get_current_client(ctx)
        return await client.obter_boleto(
            codigo_titulo=codigo_titulo,
            codigo_titulo_integracao=codigo_titulo_integracao,
        )

    @mcp.tool()
    async def prorrogar_boleto(
        ctx: Context,
        nova_data_vencimento: Annotated[str, "Nova data de vencimento do boleto (dd/mm/aaaa)"],
        codigo_titulo: Annotated[Optional[int], "Código do título no OMIE"] = None,
        codigo_titulo_integracao: Annotated[Optional[str], "Código de integração do título"] = None,
    ) -> dict:
        """Prorroga a data de vencimento do boleto de um título."""
        client = get_current_client(ctx)
        return await client.prorrogar_boleto(
            nova_data_vencimento=nova_data_vencimento,
            codigo_titulo=codigo_titulo,
            codigo_titulo_integracao=codigo_titulo_integracao,
        )

    @mcp.tool()
    async def cancelar_boleto(
        ctx: Context,
        codigo_titulo: Annotated[Optional[int], "Código do título no OMIE"] = None,
        codigo_titulo_integracao: Annotated[Optional[str], "Código de integração do título"] = None,
    ) -> dict:
        """Cancela o boleto de um título de contas a receber."""
        client = get_current_client(ctx)
        return await client.cancelar_boleto(
            codigo_titulo=codigo_titulo,
            codigo_titulo_integracao=codigo_titulo_integracao,
        )
