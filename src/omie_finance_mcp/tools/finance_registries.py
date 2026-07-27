"""Tools de Cadastros Auxiliares de Finanças — bancos, tipos de conta corrente,
contas do DRE, tipos de documento, finalidade de transferência, origem de
lançamento e bandeiras de cartão."""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def listar_bancos(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        tipo: Annotated[Optional[str], "Tipo de conta aceito pelo banco: CB | CX | CV | AC"] = None,
        nome: Annotated[Optional[str], "Filtrar por nome do banco"] = None,
    ) -> dict:
        """Lista os bancos/instituições financeiras cadastrados no OMIE."""
        client = get_current_client(ctx)
        return await client.listar_bancos(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            tipo=tipo,
            nome=nome,
        )

    @mcp.tool()
    async def consultar_banco(
        ctx: Context,
        codigo_banco: Annotated[str, "Código do banco/instituição financeira (ex: 341)"],
    ) -> dict:
        """Consulta os detalhes de um banco/instituição financeira pelo código."""
        client = get_current_client(ctx)
        return await client.consultar_banco(codigo_banco=codigo_banco)

    @mcp.tool()
    async def listar_tipos_conta_corrente(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        apenas_importado_api: Annotated[Optional[str], "Mostrar apenas registros criados via API: S ou N"] = None,
        ordenar_por: Annotated[Optional[str], "Campo de ordenação"] = None,
        ordem_decrescente: Annotated[Optional[str], "Ordem decrescente: S ou N"] = None,
    ) -> dict:
        """
        Lista os tipos de conta corrente aceitos pelo OMIE (ex: CC=conta corrente,
        CX=caixa, AC=aplicação). Use para validar o campo tipo_conta_corrente
        antes de cadastrar uma conta com incluir_conta_corrente.
        """
        client = get_current_client(ctx)
        return await client.listar_tipos_conta_corrente(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            apenas_importado_api=apenas_importado_api,
            ordenar_por=ordenar_por,
            ordem_decrescente=ordem_decrescente,
        )

    @mcp.tool()
    async def listar_categorias_dre(
        ctx: Context,
        apenas_contas_ativas: Annotated[str, "Retornar apenas contas ativas: S ou N"] = "S",
    ) -> dict:
        """Lista as contas do DRE (Demonstração de Resultado) usadas para categorizar lançamentos."""
        client = get_current_client(ctx)
        return await client.listar_categorias_dre(apenas_contas_ativas=apenas_contas_ativas)

    @mcp.tool()
    async def consultar_tipo_documento(
        ctx: Context,
        codigo: Annotated[str, "Código do tipo de documento"],
    ) -> dict:
        """Consulta um tipo de documento fiscal/financeiro pelo código."""
        client = get_current_client(ctx)
        return await client.consultar_tipo_documento(codigo=codigo)

    @mcp.tool()
    async def listar_tipos_documento(
        ctx: Context,
        codigo: Annotated[Optional[str], "Filtrar por código do tipo de documento"] = None,
    ) -> dict:
        """Pesquisa os tipos de documento cadastrados no OMIE. Omita o código para listar todos."""
        client = get_current_client(ctx)
        return await client.listar_tipos_documento(codigo=codigo)

    @mcp.tool()
    async def consultar_finalidade_transferencia(
        ctx: Context,
        codigo_banco: Annotated[str, "Código do banco/instituição financeira"],
        codigo: Annotated[str, "Código da finalidade de transferência"],
    ) -> dict:
        """Consulta uma finalidade de transferência (CNAB) de um banco específico."""
        client = get_current_client(ctx)
        return await client.consultar_finalidade_transferencia(
            codigo_banco=codigo_banco, codigo=codigo
        )

    @mcp.tool()
    async def listar_finalidades_transferencia(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
        filtrar_por_banco: Annotated[Optional[str], "Filtrar por código do banco"] = None,
    ) -> dict:
        """Lista as finalidades de transferência (CNAB) aceitas, opcionalmente filtrando por banco."""
        client = get_current_client(ctx)
        return await client.listar_finalidades_transferencia(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            filtrar_por_banco=filtrar_por_banco,
        )

    @mcp.tool()
    async def listar_origens_lancamento(
        ctx: Context,
        codigo: Annotated[Optional[str], "Filtrar por código da origem"] = None,
    ) -> dict:
        """Lista as origens de lançamento financeiro cadastradas no OMIE."""
        client = get_current_client(ctx)
        return await client.listar_origens_lancamento(codigo=codigo)

    @mcp.tool()
    async def listar_bandeiras_cartao(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página"] = 20,
    ) -> dict:
        """Lista as bandeiras de cartão de crédito/débito aceitas pelo OMIE."""
        client = get_current_client(ctx)
        return await client.listar_bandeiras_cartao(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
        )
