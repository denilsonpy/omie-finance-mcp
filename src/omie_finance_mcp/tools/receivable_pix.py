"""Tools de PIX de Contas a Receber — endpoint: /financas/pix/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def gerar_pix(
        ctx: Context,
        codigo_integracao: Annotated[str, "Código de integração próprio para esta cobrança PIX"],
        valor: Annotated[float, "Valor da cobrança"],
        codigo_titulo: Annotated[Optional[int], "Código do título de contas a receber associado"] = None,
        codigo_conta_corrente: Annotated[Optional[int], "Código da conta corrente que recebe o PIX"] = None,
        url_notificacao: Annotated[Optional[str], "URL para notificação de pagamento (webhook)"] = None,
        codigo_cliente: Annotated[Optional[int], "Código OMIE do cliente pagador"] = None,
        cnpj_cpf: Annotated[Optional[str], "CNPJ/CPF do pagador"] = None,
    ) -> dict:
        """Gera uma cobrança PIX, associada ou não a um título de contas a receber."""
        client = get_current_client(ctx)
        return await client.gerar_pix(
            codigo_integracao=codigo_integracao,
            valor=valor,
            codigo_titulo=codigo_titulo,
            codigo_conta_corrente=codigo_conta_corrente,
            url_notificacao=url_notificacao,
            codigo_cliente=codigo_cliente,
            cnpj_cpf=cnpj_cpf,
        )

    @mcp.tool()
    async def obter_pix(
        ctx: Context,
        id_pix: Annotated[Optional[int], "Código OMIE da cobrança PIX"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da cobrança PIX"] = None,
        codigo_titulo: Annotated[Optional[int], "Código do título de contas a receber associado"] = None,
    ) -> dict:
        """Consulta os detalhes de uma cobrança PIX."""
        client = get_current_client(ctx)
        return await client.obter_pix(
            id_pix=id_pix,
            codigo_integracao=codigo_integracao,
            codigo_titulo=codigo_titulo,
        )

    @mcp.tool()
    async def cancelar_pix(
        ctx: Context,
        id_pix: Annotated[Optional[int], "Código OMIE da cobrança PIX"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da cobrança PIX"] = None,
        excluir: Annotated[Optional[bool], "Se True, remove o registro em vez de apenas cancelar"] = None,
    ) -> dict:
        """Cancela uma cobrança PIX."""
        client = get_current_client(ctx)
        return await client.cancelar_pix(
            id_pix=id_pix,
            codigo_integracao=codigo_integracao,
            excluir=excluir,
        )

    @mcp.tool()
    async def listar_pix(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        emissao_de: Annotated[Optional[str], "Data de emissão inicial (dd/mm/aaaa)"] = None,
        emissao_ate: Annotated[Optional[str], "Data de emissão final (dd/mm/aaaa)"] = None,
        status: Annotated[Optional[str], "Filtrar por status da cobrança"] = None,
    ) -> dict:
        """Lista cobranças PIX geradas, com filtros por período de emissão e status."""
        client = get_current_client(ctx)
        return await client.listar_pix(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            emissao_de=emissao_de,
            emissao_ate=emissao_ate,
            status=status,
        )

    @mcp.tool()
    async def listar_status_pix(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        emissao_de: Annotated[Optional[str], "Data de emissão inicial (dd/mm/aaaa)"] = None,
        emissao_ate: Annotated[Optional[str], "Data de emissão final (dd/mm/aaaa)"] = None,
        status: Annotated[Optional[str], "Filtrar por status da cobrança"] = None,
    ) -> dict:
        """Lista apenas o status das cobranças PIX geradas (consulta mais leve que listar_pix)."""
        client = get_current_client(ctx)
        return await client.listar_status_pix(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            emissao_de=emissao_de,
            emissao_ate=emissao_ate,
            status=status,
        )

    @mcp.tool()
    async def obter_status_pix(
        ctx: Context,
        id_pix: Annotated[Optional[int], "Código OMIE da cobrança PIX"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da cobrança PIX"] = None,
        codigo_titulo: Annotated[Optional[int], "Código do título de contas a receber associado"] = None,
    ) -> dict:
        """Consulta apenas o status de uma cobrança PIX específica."""
        client = get_current_client(ctx)
        return await client.obter_status_pix(
            id_pix=id_pix,
            codigo_integracao=codigo_integracao,
            codigo_titulo=codigo_titulo,
        )

    @mcp.tool()
    async def gerar_qrcode_pix_estatico(
        ctx: Context,
        codigo_conta_corrente: Annotated[Optional[int], "Código da conta corrente que recebe o PIX"] = None,
    ) -> dict:
        """Gera um QR Code PIX estático (sem valor fixo) para uma conta corrente."""
        client = get_current_client(ctx)
        return await client.gerar_qrcode_pix_estatico(
            codigo_conta_corrente=codigo_conta_corrente,
        )
