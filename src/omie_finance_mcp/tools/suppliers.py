"""Tools de Fornecedores — endpoint: /geral/clientes/"""

from typing import Annotated, Optional
from mcp.server.fastmcp import FastMCP, Context

from ..auth import get_current_client


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def listar_fornecedores(
        ctx: Context,
        pagina: Annotated[int, "Número da página (inicia em 1)"] = 1,
        registros_por_pagina: Annotated[int, "Registros por página (máx 50)"] = 20,
        apenas_fornecedor: Annotated[str, "Filtrar apenas fornecedores: S ou N"] = "S",
        filtrar_por_nome: Annotated[Optional[str], "Filtrar por nome/razão social"] = None,
        filtrar_por_cnpj: Annotated[Optional[str], "Filtrar por CNPJ/CPF"] = None,
    ) -> dict:
        """Lista fornecedores cadastrados no OMIE com paginação e filtros."""
        client = get_current_client(ctx)
        return await client.listar_fornecedores(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            apenas_fornecedor=apenas_fornecedor,
            filtrar_por_nome=filtrar_por_nome,
            filtrar_por_cnpj=filtrar_por_cnpj,
        )

    @mcp.tool()
    async def consultar_fornecedor(
        ctx: Context,
        codigo_cliente_omie: Annotated[Optional[int], "Código do fornecedor no OMIE"] = None,
        codigo_cliente_integracao: Annotated[Optional[str], "Código de integração do fornecedor"] = None,
        cnpj_cpf: Annotated[Optional[str], "CNPJ ou CPF do fornecedor"] = None,
    ) -> dict:
        """Consulta detalhes de um fornecedor específico. Informe ao menos um dos identificadores."""
        client = get_current_client(ctx)
        return await client.consultar_fornecedor(
            codigo_cliente_omie=codigo_cliente_omie,
            codigo_cliente_integracao=codigo_cliente_integracao,
            cnpj_cpf=cnpj_cpf,
        )

    @mcp.tool()
    async def incluir_fornecedor(
        ctx: Context,
        razao_social: Annotated[str, "Razão social do fornecedor"],
        cnpj_cpf: Annotated[str, "CNPJ ou CPF"],
        email: Annotated[str, "E-mail do fornecedor"],
        nome_fantasia: Annotated[Optional[str], "Nome fantasia"] = None,
        telefone1_ddd: Annotated[Optional[str], "DDD do telefone principal"] = None,
        telefone1_numero: Annotated[Optional[str], "Número do telefone principal"] = None,
        endereco: Annotated[Optional[str], "Logradouro"] = None,
        endereco_numero: Annotated[Optional[str], "Número do endereço"] = None,
        bairro: Annotated[Optional[str], "Bairro"] = None,
        cidade: Annotated[Optional[str], "Cidade"] = None,
        estado: Annotated[Optional[str], "UF (ex: SP)"] = None,
        cep: Annotated[Optional[str], "CEP"] = None,
        codigo_cliente_integracao: Annotated[Optional[str], "Código de integração próprio"] = None,
        tags: Annotated[Optional[str], "Tags separadas por vírgula (ex: fornecedor,prioritario)"] = None,
    ) -> dict:
        """Cadastra um novo fornecedor no OMIE."""
        client = get_current_client(ctx)
        return await client.incluir_fornecedor(
            razao_social=razao_social,
            cnpj_cpf=cnpj_cpf,
            email=email,
            nome_fantasia=nome_fantasia,
            telefone1_ddd=telefone1_ddd,
            telefone1_numero=telefone1_numero,
            endereco=endereco,
            endereco_numero=endereco_numero,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            cep=cep,
            codigo_cliente_integracao=codigo_cliente_integracao,
            tags=tags,
        )

    @mcp.tool()
    async def alterar_fornecedor(
        ctx: Context,
        codigo_cliente_omie: Annotated[Optional[int], "Código do fornecedor no OMIE"] = None,
        codigo_cliente_integracao: Annotated[Optional[str], "Código de integração"] = None,
        razao_social: Annotated[Optional[str], "Nova razão social"] = None,
        email: Annotated[Optional[str], "Novo e-mail"] = None,
        telefone1_ddd: Annotated[Optional[str], "DDD do telefone"] = None,
        telefone1_numero: Annotated[Optional[str], "Número do telefone"] = None,
        endereco: Annotated[Optional[str], "Logradouro"] = None,
        endereco_numero: Annotated[Optional[str], "Número do endereço"] = None,
        bairro: Annotated[Optional[str], "Bairro"] = None,
        cidade: Annotated[Optional[str], "Cidade"] = None,
        estado: Annotated[Optional[str], "UF (ex: SP)"] = None,
        cep: Annotated[Optional[str], "CEP"] = None,
    ) -> dict:
        """Altera dados de um fornecedor existente no OMIE."""
        client = get_current_client(ctx)
        return await client.alterar_fornecedor(
            codigo_cliente_omie=codigo_cliente_omie,
            codigo_cliente_integracao=codigo_cliente_integracao,
            razao_social=razao_social,
            email=email,
            telefone1_ddd=telefone1_ddd,
            telefone1_numero=telefone1_numero,
            endereco=endereco,
            endereco_numero=endereco_numero,
            bairro=bairro,
            cidade=cidade,
            estado=estado,
            cep=cep,
        )
