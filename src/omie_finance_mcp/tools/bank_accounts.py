"""Tools de Contas Correntes e Extrato — endpoints: /geral/contacorrente/ e /financas/extrato/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def listar_contas_correntes(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
    ) -> dict:
        """Lista todas as contas correntes/bancárias cadastradas no OMIE."""
        client = get_current_client(ctx)
        return await client.listar_contas_correntes(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
        )

    @mcp.tool()
    async def consultar_conta_corrente(
        ctx: Context,
        codigo_conta_corrente: Annotated[Optional[int], "Código OMIE da conta corrente"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da conta corrente"] = None,
    ) -> dict:
        """Consulta detalhes de uma conta corrente específica."""
        client = get_current_client(ctx)
        return await client.consultar_conta_corrente(
            codigo_conta_corrente=codigo_conta_corrente,
            codigo_integracao=codigo_integracao,
        )

    @mcp.tool()
    async def incluir_conta_corrente(
        ctx: Context,
        descricao: Annotated[str, "Descrição/apelido da conta corrente"],
        tipo_conta_corrente: Annotated[
            str,
            "Tipo: AC | AD | CA | CC | CE | CG | CN | CP | CR | CV | CX | MT | PG "
            "— use listar_tipos_conta_corrente para ver as opções",
        ],
        codigo_banco: Annotated[Optional[str], "Código do banco (ex: 341)"] = None,
        codigo_agencia: Annotated[Optional[str], "Código da agência"] = None,
        numero_conta_corrente: Annotated[Optional[str], "Número da conta"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração próprio"] = None,
        saldo_inicial: Annotated[Optional[float], "Saldo inicial da conta"] = None,
        saldo_data: Annotated[Optional[str], "Data do saldo inicial (dd/mm/aaaa)"] = None,
        valor_limite: Annotated[Optional[float], "Limite de crédito da conta"] = None,
        ocultar_do_fluxo: Annotated[Optional[str], "Ocultar do fluxo de caixa: S ou N"] = None,
        ocultar_do_resumo: Annotated[Optional[str], "Ocultar do resumo financeiro: S ou N"] = None,
        observacao: Annotated[Optional[str], "Observações"] = None,
    ) -> dict:
        """Cadastra uma nova conta corrente/bancária no OMIE."""
        client = get_current_client(ctx)
        return await client.incluir_conta_corrente(
            descricao=descricao,
            tipo_conta_corrente=tipo_conta_corrente,
            codigo_banco=codigo_banco,
            codigo_agencia=codigo_agencia,
            numero_conta_corrente=numero_conta_corrente,
            codigo_integracao=codigo_integracao,
            saldo_inicial=saldo_inicial,
            saldo_data=saldo_data,
            valor_limite=valor_limite,
            ocultar_do_fluxo=ocultar_do_fluxo,
            ocultar_do_resumo=ocultar_do_resumo,
            observacao=observacao,
        )

    @mcp.tool()
    async def alterar_conta_corrente(
        ctx: Context,
        codigo_conta_corrente: Annotated[Optional[int], "Código OMIE da conta corrente"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da conta corrente"] = None,
        descricao: Annotated[Optional[str], "Nova descrição/apelido da conta"] = None,
        tipo_conta_corrente: Annotated[Optional[str], "Novo tipo de conta corrente"] = None,
        codigo_banco: Annotated[Optional[str], "Código do banco (ex: 341)"] = None,
        codigo_agencia: Annotated[Optional[str], "Código da agência"] = None,
        numero_conta_corrente: Annotated[Optional[str], "Número da conta"] = None,
        saldo_inicial: Annotated[Optional[float], "Saldo inicial da conta"] = None,
        saldo_data: Annotated[Optional[str], "Data do saldo inicial (dd/mm/aaaa)"] = None,
        valor_limite: Annotated[Optional[float], "Limite de crédito da conta"] = None,
        ocultar_do_fluxo: Annotated[Optional[str], "Ocultar do fluxo de caixa: S ou N"] = None,
        ocultar_do_resumo: Annotated[Optional[str], "Ocultar do resumo financeiro: S ou N"] = None,
        observacao: Annotated[Optional[str], "Observações"] = None,
    ) -> dict:
        """
        Altera uma conta corrente existente. Informe codigo_conta_corrente ou
        codigo_integracao para identificar a conta; os demais campos são
        opcionais e só os informados são atualizados.
        """
        client = get_current_client(ctx)
        return await client.alterar_conta_corrente(
            codigo_conta_corrente=codigo_conta_corrente,
            codigo_integracao=codigo_integracao,
            descricao=descricao,
            tipo_conta_corrente=tipo_conta_corrente,
            codigo_banco=codigo_banco,
            codigo_agencia=codigo_agencia,
            numero_conta_corrente=numero_conta_corrente,
            saldo_inicial=saldo_inicial,
            saldo_data=saldo_data,
            valor_limite=valor_limite,
            ocultar_do_fluxo=ocultar_do_fluxo,
            ocultar_do_resumo=ocultar_do_resumo,
            observacao=observacao,
        )

    @mcp.tool()
    async def excluir_conta_corrente(
        ctx: Context,
        codigo_conta_corrente: Annotated[Optional[int], "Código OMIE da conta corrente"] = None,
        codigo_integracao: Annotated[Optional[str], "Código de integração da conta corrente"] = None,
    ) -> dict:
        """Exclui uma conta corrente do OMIE. Informe codigo_conta_corrente ou codigo_integracao."""
        client = get_current_client(ctx)
        return await client.excluir_conta_corrente(
            codigo_conta_corrente=codigo_conta_corrente,
            codigo_integracao=codigo_integracao,
        )

    @mcp.tool()
    async def consultar_extrato_bancario(
        ctx: Context,
        data_inicio: Annotated[str, "Data inicial do extrato (dd/mm/aaaa)"],
        data_fim: Annotated[str, "Data final do extrato (dd/mm/aaaa)"],
        codigo_conta_corrente: Annotated[Optional[int], "Código OMIE da conta corrente"] = None,
        codigo_integracao_conta: Annotated[Optional[str], "Código de integração da conta corrente"] = None,
        exibir_apenas_saldo: Annotated[str, "Exibir apenas saldo final: S ou N"] = "N",
    ) -> dict:
        """
        Consulta o extrato bancário de uma conta corrente em um período.
        Retorna todos os lançamentos e o saldo do período.
        Informe codigo_conta_corrente ou codigo_integracao_conta — o OMIE exige um deles.
        Use listar_contas_correntes para descobrir o código (nCodCC).
        """
        client = get_current_client(ctx)
        return await client.consultar_extrato_bancario(
            data_inicio=data_inicio,
            data_fim=data_fim,
            codigo_conta_corrente=codigo_conta_corrente,
            codigo_integracao_conta=codigo_integracao_conta,
            exibir_apenas_saldo=exibir_apenas_saldo,
        )
