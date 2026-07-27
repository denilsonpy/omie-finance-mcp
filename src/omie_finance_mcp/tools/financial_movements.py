"""Tools de Movimentos Financeiros — endpoint: /financas/mf/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def listar_movimentos_financeiros(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        ordenar_por: Annotated[Optional[str], "Ordenação: CODIGO | CODIGO_INTEGRACAO"] = None,
        incluir_dados_cadastrais: Annotated[Optional[bool], "Incluir dados cadastrais do cliente/fornecedor"] = None,
        emissao_de: Annotated[Optional[str], "Data de emissão inicial (dd/mm/aaaa)"] = None,
        emissao_ate: Annotated[Optional[str], "Data de emissão final (dd/mm/aaaa)"] = None,
        vencimento_de: Annotated[Optional[str], "Data de vencimento inicial (dd/mm/aaaa)"] = None,
        vencimento_ate: Annotated[Optional[str], "Data de vencimento final (dd/mm/aaaa)"] = None,
        pagamento_de: Annotated[Optional[str], "Data de pagamento/recebimento inicial (dd/mm/aaaa)"] = None,
        pagamento_ate: Annotated[Optional[str], "Data de pagamento/recebimento final (dd/mm/aaaa)"] = None,
        codigo_cliente: Annotated[Optional[int], "Código OMIE do cliente/fornecedor"] = None,
        cnpj_cpf_cliente: Annotated[Optional[str], "CNPJ/CPF do cliente/fornecedor"] = None,
        natureza: Annotated[Optional[str], "Natureza: PAGAR | RECEBER"] = None,
        status: Annotated[Optional[str], "Status do lançamento"] = None,
        tipo_lancamento: Annotated[
            Optional[str],
            "Tipo de registro: CP (contas a pagar) | CR (contas a receber) | "
            "CPCR (ambos) | BX (baixas) | CC (conta corrente)",
        ] = None,
    ) -> dict:
        """
        Consulta unificada de movimentos financeiros: títulos a pagar/receber,
        baixas (pagamentos/recebimentos já efetivados) e lançamentos de conta
        corrente num único resultado. Diferente de pesquisar_lancamentos_financeiros,
        que traz apenas títulos — aqui também aparecem as baixas já realizadas.
        """
        client = get_current_client(ctx)
        return await client.listar_movimentos_financeiros(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            ordenar_por=ordenar_por,
            incluir_dados_cadastrais=incluir_dados_cadastrais,
            emissao_de=emissao_de,
            emissao_ate=emissao_ate,
            vencimento_de=vencimento_de,
            vencimento_ate=vencimento_ate,
            pagamento_de=pagamento_de,
            pagamento_ate=pagamento_ate,
            codigo_cliente=codigo_cliente,
            cnpj_cpf_cliente=cnpj_cpf_cliente,
            natureza=natureza,
            status=status,
            tipo_lancamento=tipo_lancamento,
        )
