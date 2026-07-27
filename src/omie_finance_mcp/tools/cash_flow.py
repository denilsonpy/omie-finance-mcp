"""Tools de Fluxo de Caixa e Resumo Financeiro — endpoints: /financas/caixa/ e /financas/resumo/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def consultar_fluxo_caixa(
        ctx: Context,
        ano: Annotated[int, "Ano de referência (ex: 2025)"],
        mes: Annotated[int, "Mês de referência (1-12)"],
    ) -> dict:
        """
        Consulta o fluxo de caixa do mês, comparando valores previstos vs realizados
        por categoria financeira.
        """
        client = get_current_client(ctx)
        return await client.consultar_fluxo_caixa(ano=ano, mes=mes)

    @mcp.tool()
    async def obter_resumo_financeiro(
        ctx: Context,
        data: Annotated[str, "Data de referência do resumo (dd/mm/aaaa)"],
        exibir_categoria: Annotated[bool, "Detalhar os valores por categoria financeira"] = False,
        apenas_resumo: Annotated[bool, "Retornar somente os totais, sem os lançamentos"] = True,
    ) -> dict:
        """
        Obtém o resumo financeiro consolidado numa data de referência, incluindo
        totais de contas a pagar, a receber e saldo bancário.
        Observação: o OMIE calcula este resumo para um único dia, não para um período.
        """
        client = get_current_client(ctx)
        return await client.obter_resumo_financeiro(
            data=data,
            exibir_categoria=exibir_categoria,
            apenas_resumo=apenas_resumo,
        )

    @mcp.tool()
    async def listar_titulos_em_aberto(
        ctx: Context,
        tipo: Annotated[str, "Tipo de título: PAGAR | RECEBER"],
        data: Annotated[Optional[str], "Data de referência (dd/mm/aaaa)"] = None,
        codigo_cliente: Annotated[Optional[int], "Filtrar por código OMIE do cliente/fornecedor"] = None,
        nome_cliente: Annotated[Optional[str], "Filtrar por nome do cliente/fornecedor"] = None,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página (máx 50)"] = 20,
    ) -> dict:
        """
        Lista os títulos financeiros em aberto (não liquidados) de um tipo.
        O OMIE atende um tipo por chamada: use PAGAR ou RECEBER.
        """
        client = get_current_client(ctx)
        return await client.listar_titulos_em_aberto(
            tipo=tipo,
            data=data,
            codigo_cliente=codigo_cliente,
            nome_cliente=nome_cliente,
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
        )

    @mcp.tool()
    async def pesquisar_lancamentos_financeiros(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página (máx 50)"] = 20,
        natureza: Annotated[
            Optional[str],
            "Natureza do título: PAGAR | RECEBER. Omita para trazer ambos.",
        ] = None,
        vencimento_de: Annotated[Optional[str], "Vencimento inicial (dd/mm/aaaa)"] = None,
        vencimento_ate: Annotated[Optional[str], "Vencimento final (dd/mm/aaaa)"] = None,
        emissao_de: Annotated[Optional[str], "Emissão inicial (dd/mm/aaaa)"] = None,
        emissao_ate: Annotated[Optional[str], "Emissão final (dd/mm/aaaa)"] = None,
        codigo_cliente: Annotated[Optional[int], "Código OMIE do cliente/fornecedor"] = None,
        codigo_conta_corrente: Annotated[Optional[int], "Filtrar por conta corrente"] = None,
        status: Annotated[
            Optional[str],
            "Status: CANCELADO | PAGO | LIQUIDADO | EMABERTO | ATRASADO | AVENCER",
        ] = None,
    ) -> dict:
        """
        Pesquisa lançamentos financeiros de forma unificada (contas a pagar + a receber).
        Ideal para visão consolidada das finanças.
        """
        client = get_current_client(ctx)
        return await client.pesquisar_lancamentos_financeiros(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            natureza=natureza,
            vencimento_de=vencimento_de,
            vencimento_ate=vencimento_ate,
            emissao_de=emissao_de,
            emissao_ate=emissao_ate,
            codigo_cliente=codigo_cliente,
            codigo_conta_corrente=codigo_conta_corrente,
            status=status,
        )
