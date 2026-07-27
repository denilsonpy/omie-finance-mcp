"""Tools de Lançamentos em Conta Corrente (Transações Bancárias) — endpoint: /financas/contacorrentelancamentos/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def listar_lancamentos_bancarios(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página (máx 50)"] = 20,
        codigo_conta_corrente: Annotated[Optional[int], "Filtrar por conta corrente"] = None,
        data_lancamento_de: Annotated[Optional[str], "Data de lançamento inicial (dd/mm/aaaa)"] = None,
        data_lancamento_ate: Annotated[Optional[str], "Data de lançamento final (dd/mm/aaaa)"] = None,
        data_inclusao_de: Annotated[Optional[str], "Data de inclusão inicial (dd/mm/aaaa)"] = None,
        data_inclusao_ate: Annotated[Optional[str], "Data de inclusão final (dd/mm/aaaa)"] = None,
        ordem_descrescente: Annotated[str, "Ordem decrescente: S ou N"] = "S",
    ) -> dict:
        """Lista lançamentos/transações bancárias em conta corrente."""
        client = get_current_client(ctx)
        return await client.listar_lancamentos_bancarios(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            codigo_conta_corrente=codigo_conta_corrente,
            data_lancamento_de=data_lancamento_de,
            data_lancamento_ate=data_lancamento_ate,
            data_inclusao_de=data_inclusao_de,
            data_inclusao_ate=data_inclusao_ate,
            ordem_descrescente=ordem_descrescente,
        )

    @mcp.tool()
    async def consultar_lancamento_bancario(
        ctx: Context,
        codigo_lancamento: Annotated[Optional[int], "Código do lançamento no OMIE"] = None,
        codigo_lancamento_integracao: Annotated[Optional[str], "Código de integração do lançamento"] = None,
    ) -> dict:
        """Consulta detalhes de um lançamento bancário específico."""
        client = get_current_client(ctx)
        return await client.consultar_lancamento_bancario(
            codigo_lancamento=codigo_lancamento,
            codigo_lancamento_integracao=codigo_lancamento_integracao,
        )

    @mcp.tool()
    async def incluir_lancamento_bancario(
        ctx: Context,
        codigo_conta_corrente: Annotated[int, "Código da conta corrente"],
        data_lancamento: Annotated[str, "Data do lançamento (dd/mm/aaaa)"],
        valor: Annotated[float, "Valor do lançamento (positivo=crédito, negativo=débito)"],
        codigo_categoria: Annotated[str, "Código da categoria financeira"],
        tipo_documento: Annotated[
            str,
            "Tipo: PIX | TED | DOC | BOL | CHQ | DEB | DIN | TRA | CRE | 99999 (outros)",
        ] = "99999",
        numero_documento: Annotated[Optional[str], "Número do documento"] = None,
        codigo_cliente: Annotated[Optional[int], "Código OMIE do cliente/fornecedor"] = None,
        codigo_conta_destino: Annotated[Optional[int], "Código da conta destino (para transferências)"] = None,
        observacao: Annotated[Optional[str], "Observações"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração próprio"] = None,
    ) -> dict:
        """Cria um lançamento manual em conta corrente (débito ou crédito)."""
        client = get_current_client(ctx)
        return await client.incluir_lancamento_bancario(
            codigo_conta_corrente=codigo_conta_corrente,
            data_lancamento=data_lancamento,
            valor=valor,
            codigo_categoria=codigo_categoria,
            tipo_documento=tipo_documento,
            numero_documento=numero_documento,
            codigo_cliente=codigo_cliente,
            codigo_conta_destino=codigo_conta_destino,
            observacao=observacao,
            codigo_integracao=codigo_integracao,
        )

    @mcp.tool()
    async def excluir_lancamento_bancario(
        ctx: Context,
        codigo_lancamento: Annotated[Optional[int], "Código do lançamento no OMIE"] = None,
        codigo_lancamento_integracao: Annotated[Optional[str], "Código de integração do lançamento"] = None,
    ) -> dict:
        """Exclui um lançamento bancário em conta corrente."""
        client = get_current_client(ctx)
        return await client.excluir_lancamento_bancario(
            codigo_lancamento=codigo_lancamento,
            codigo_lancamento_integracao=codigo_lancamento_integracao,
        )
