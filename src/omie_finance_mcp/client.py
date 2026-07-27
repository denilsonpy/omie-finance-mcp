"""Cliente HTTP para a API do OMIE ERP.

Além de `call()`, que executa qualquer método de qualquer endpoint do OMIE,
este cliente expõe um método nomeado por operação (ex: `listar_contas_pagar`,
`incluir_conta_receber`). Esses métodos concentram o conhecimento de endpoint,
nome da chamada e formato dos parâmetros de cada operação, permitindo usar o
OmieClient diretamente — sem depender do MCP/FastMCP — em qualquer outro
lugar que precise falar com a API do OMIE.
"""

import httpx
from typing import Any, Optional


OMIE_BASE_URL = "https://app.omie.com.br/api/v1"

# O OMIE sinaliza "nenhum registro encontrado" com HTTP 500 + este faultcode.
# Não é um erro: é uma lista vazia.
FAULTCODE_SEM_REGISTROS = "5113"


class OmieError(Exception):
    """Erro retornado pela API do OMIE (faultstring/faultcode)."""

    def __init__(self, status_code: int, faultcode: str, faultstring: str, call: str):
        self.status_code = status_code
        self.faultcode = faultcode
        self.faultstring = faultstring
        self.call = call
        super().__init__(f"[{call}] HTTP {status_code} {faultcode}: {faultstring}")

    @property
    def sem_registros(self) -> bool:
        return FAULTCODE_SEM_REGISTROS in self.faultcode


class OmieClient:
    """Cliente para chamadas à API REST do OMIE."""

    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self._http = httpx.AsyncClient(timeout=30.0)

    async def call(
        self,
        endpoint: str,
        call: str,
        params: dict[str, Any] | None = None,
        *,
        lista_vazia_ok: bool = False,
    ) -> dict[str, Any]:
        """
        Executa uma chamada à API do OMIE.

        Args:
            endpoint:       Caminho do endpoint (ex: "geral/clientes/")
            call:           Nome do método da API (ex: "ListarClientes")
            params:         Parâmetros específicos do método
            lista_vazia_ok: Traduz "não existem registros" (500/5113) numa lista
                            vazia em vez de erro. Use nos métodos de listagem.

        Returns:
            Resposta da API como dicionário.

        Raises:
            OmieError: quando a API retorna um faultstring.
        """
        payload = {
            "call": call,
            "app_key": self.app_key,
            "app_secret": self.app_secret,
            "param": [params or {}],
        }

        url = f"{OMIE_BASE_URL}/{endpoint}"
        response = await self._http.post(url, json=payload)

        try:
            body = response.json()
        except ValueError:
            response.raise_for_status()
            raise OmieError(response.status_code, "", response.text[:500], call)

        # O OMIE devolve erros de validação como HTTP 500 com um faultstring
        # descritivo. Sem isto, o erro chega ao usuário como um 500 opaco.
        if isinstance(body, dict) and "faultstring" in body:
            erro = OmieError(
                response.status_code,
                str(body.get("faultcode", "")),
                str(body["faultstring"]).strip(),
                call,
            )
            if lista_vazia_ok and erro.sem_registros:
                return {"registros": 0, "total_de_registros": 0, "total_de_paginas": 0, "lista": []}
            raise erro

        response.raise_for_status()
        return body

    async def aclose(self):
        await self._http.aclose()

    # ------------------------------------------------------------------
    # Fornecedores — geral/clientes/
    # ------------------------------------------------------------------

    async def listar_fornecedores(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        apenas_fornecedor: str = "S",
        filtrar_por_nome: Optional[str] = None,
        filtrar_por_cnpj: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
        }
        filtro: dict = {}
        # No OMIE não existe flag de fornecedor no cadastro: a distinção é feita
        # pela tag "Fornecedor" aplicada ao cliente.
        if apenas_fornecedor == "S":
            filtro["tags"] = [{"tag": "Fornecedor"}]
        if filtrar_por_nome:
            filtro["razao_social"] = filtrar_por_nome
        if filtrar_por_cnpj:
            filtro["cnpj_cpf"] = filtrar_por_cnpj
        if filtro:
            params["clientesFiltro"] = filtro
        return await self.call("geral/clientes/", "ListarClientes", params, lista_vazia_ok=True)

    async def consultar_fornecedor(
        self,
        codigo_cliente_omie: Optional[int] = None,
        codigo_cliente_integracao: Optional[str] = None,
        cnpj_cpf: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_cliente_omie:
            params["codigo_cliente_omie"] = codigo_cliente_omie
        if codigo_cliente_integracao:
            params["codigo_cliente_integracao"] = codigo_cliente_integracao
        if cnpj_cpf:
            params["cnpj_cpf"] = cnpj_cpf
        return await self.call("geral/clientes/", "ConsultarCliente", params)

    async def incluir_fornecedor(
        self,
        razao_social: str,
        cnpj_cpf: str,
        email: str,
        nome_fantasia: Optional[str] = None,
        telefone1_ddd: Optional[str] = None,
        telefone1_numero: Optional[str] = None,
        endereco: Optional[str] = None,
        endereco_numero: Optional[str] = None,
        bairro: Optional[str] = None,
        cidade: Optional[str] = None,
        estado: Optional[str] = None,
        cep: Optional[str] = None,
        codigo_cliente_integracao: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "razao_social": razao_social,
            "cnpj_cpf": cnpj_cpf,
            "email": email,
            "fornecedor": "S",
        }
        if nome_fantasia:
            params["nome_fantasia"] = nome_fantasia
        if telefone1_ddd:
            params["telefone1_ddd"] = telefone1_ddd
        if telefone1_numero:
            params["telefone1_numero"] = telefone1_numero
        if endereco:
            params["endereco"] = endereco
        if endereco_numero:
            params["endereco_numero"] = endereco_numero
        if bairro:
            params["bairro"] = bairro
        if cidade:
            params["cidade"] = cidade
        if estado:
            params["estado"] = estado
        if cep:
            params["cep"] = cep
        if codigo_cliente_integracao:
            params["codigo_cliente_integracao"] = codigo_cliente_integracao
        if tags:
            params["tags"] = [{"tag": t.strip()} for t in tags.split(",")]
        return await self.call("geral/clientes/", "IncluirCliente", params)

    async def alterar_fornecedor(
        self,
        codigo_cliente_omie: Optional[int] = None,
        codigo_cliente_integracao: Optional[str] = None,
        razao_social: Optional[str] = None,
        email: Optional[str] = None,
        telefone1_ddd: Optional[str] = None,
        telefone1_numero: Optional[str] = None,
        endereco: Optional[str] = None,
        endereco_numero: Optional[str] = None,
        bairro: Optional[str] = None,
        cidade: Optional[str] = None,
        estado: Optional[str] = None,
        cep: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_cliente_omie:
            params["codigo_cliente_omie"] = codigo_cliente_omie
        if codigo_cliente_integracao:
            params["codigo_cliente_integracao"] = codigo_cliente_integracao
        for field, value in [
            ("razao_social", razao_social), ("email", email),
            ("telefone1_ddd", telefone1_ddd), ("telefone1_numero", telefone1_numero),
            ("endereco", endereco), ("endereco_numero", endereco_numero),
            ("bairro", bairro), ("cidade", cidade), ("estado", estado), ("cep", cep),
        ]:
            if value is not None:
                params[field] = value
        return await self.call("geral/clientes/", "AlterarCliente", params)

    # ------------------------------------------------------------------
    # Contas a Pagar — financas/contapagar/
    # ------------------------------------------------------------------

    async def listar_contas_pagar(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        filtrar_por_status: Optional[str] = None,
        filtrar_por_data_de: Optional[str] = None,
        filtrar_por_data_ate: Optional[str] = None,
        filtrar_cliente: Optional[int] = None,
        filtrar_conta_corrente: Optional[int] = None,
        ordenar_por: str = "DATA_VENCIMENTO",
        ordem_descrescente: str = "N",
    ) -> dict:
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
            "ordenar_por": ordenar_por,
            "ordem_descrescente": ordem_descrescente,
        }
        if filtrar_por_status:
            params["filtrar_por_status"] = filtrar_por_status
        if filtrar_por_data_de:
            params["filtrar_por_data_de"] = filtrar_por_data_de
        if filtrar_por_data_ate:
            params["filtrar_por_data_ate"] = filtrar_por_data_ate
        if filtrar_cliente:
            params["filtrar_cliente"] = filtrar_cliente
        if filtrar_conta_corrente:
            params["filtrar_conta_corrente"] = filtrar_conta_corrente
        return await self.call(
            "financas/contapagar/", "ListarContasPagar", params, lista_vazia_ok=True
        )

    async def consultar_conta_pagar(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_lancamento_omie:
            params["codigo_lancamento_omie"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        return await self.call("financas/contapagar/", "ConsultarContaPagar", params)

    async def incluir_conta_pagar(
        self,
        codigo_cliente_fornecedor: int,
        data_vencimento: str,
        valor_documento: float,
        codigo_categoria: str,
        data_previsao: str,
        codigo_lancamento_integracao: Optional[str] = None,
        numero_documento: Optional[str] = None,
        data_emissao: Optional[str] = None,
        id_conta_corrente: Optional[int] = None,
        observacao: Optional[str] = None,
        numero_pedido: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "codigo_cliente_fornecedor": codigo_cliente_fornecedor,
            "data_vencimento": data_vencimento,
            "valor_documento": valor_documento,
            "codigo_categoria": codigo_categoria,
            "data_previsao": data_previsao,
        }
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if numero_documento:
            params["numero_documento"] = numero_documento
        if data_emissao:
            params["data_emissao"] = data_emissao
        if id_conta_corrente:
            params["id_conta_corrente"] = id_conta_corrente
        if observacao:
            params["observacao"] = observacao
        if numero_pedido:
            params["numero_pedido"] = numero_pedido
        return await self.call("financas/contapagar/", "IncluirContaPagar", params)

    async def alterar_conta_pagar(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
        codigo_cliente_fornecedor: Optional[int] = None,
        data_vencimento: Optional[str] = None,
        valor_documento: Optional[float] = None,
        codigo_categoria: Optional[str] = None,
        data_previsao: Optional[str] = None,
        numero_documento: Optional[str] = None,
        data_emissao: Optional[str] = None,
        id_conta_corrente: Optional[int] = None,
        observacao: Optional[str] = None,
        numero_pedido: Optional[str] = None,
    ) -> dict:
        if not codigo_lancamento_omie and not codigo_lancamento_integracao:
            raise ValueError(
                "Informe codigo_lancamento_omie ou codigo_lancamento_integracao "
                "para identificar o título a alterar."
            )
        params: dict = {}
        if codigo_lancamento_omie:
            params["codigo_lancamento_omie"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if codigo_cliente_fornecedor:
            params["codigo_cliente_fornecedor"] = codigo_cliente_fornecedor
        if data_vencimento:
            params["data_vencimento"] = data_vencimento
        if valor_documento is not None:
            params["valor_documento"] = valor_documento
        if codigo_categoria:
            params["codigo_categoria"] = codigo_categoria
        if data_previsao:
            params["data_previsao"] = data_previsao
        if numero_documento:
            params["numero_documento"] = numero_documento
        if data_emissao:
            params["data_emissao"] = data_emissao
        if id_conta_corrente:
            params["id_conta_corrente"] = id_conta_corrente
        if observacao:
            params["observacao"] = observacao
        if numero_pedido:
            params["numero_pedido"] = numero_pedido
        return await self.call("financas/contapagar/", "AlterarContaPagar", params)

    async def lancar_pagamento(
        self,
        codigo_conta_corrente: int,
        valor: float,
        data: str,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
        desconto: float = 0.0,
        juros: float = 0.0,
        multa: float = 0.0,
        observacao: Optional[str] = None,
        conciliar_documento: str = "N",
    ) -> dict:
        params: dict = {
            "codigo_conta_corrente": codigo_conta_corrente,
            "valor": valor,
            "data": data,
            "desconto": desconto,
            "juros": juros,
            "multa": multa,
            "conciliar_documento": conciliar_documento,
        }
        # A baixa identifica o título por [codigo_lancamento], não por
        # [codigo_lancamento_omie] (esse é o nome usado só nos métodos de chave).
        if codigo_lancamento_omie:
            params["codigo_lancamento"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if observacao:
            params["observacao"] = observacao
        return await self.call("financas/contapagar/", "LancarPagamento", params)

    async def cancelar_pagamento_conta_pagar(
        self,
        codigo_baixa: Optional[int] = None,
        codigo_baixa_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_baixa:
            params["codigo_baixa"] = codigo_baixa
        if codigo_baixa_integracao:
            params["codigo_baixa_integracao"] = codigo_baixa_integracao
        return await self.call("financas/contapagar/", "CancelarPagamento", params)

    async def excluir_conta_pagar(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_lancamento_omie:
            params["codigo_lancamento_omie"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        return await self.call("financas/contapagar/", "ExcluirContaPagar", params)

    # ------------------------------------------------------------------
    # Contas a Receber — financas/contareceber/
    # ------------------------------------------------------------------

    async def listar_contas_receber(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        filtrar_por_status: Optional[str] = None,
        filtrar_por_data_de: Optional[str] = None,
        filtrar_por_data_ate: Optional[str] = None,
        filtrar_por_emissao_de: Optional[str] = None,
        filtrar_por_emissao_ate: Optional[str] = None,
        filtrar_cliente: Optional[int] = None,
        filtrar_conta_corrente: Optional[int] = None,
        filtrar_apenas_titulos_em_aberto: str = "N",
        ordenar_por: str = "DATA_VENCIMENTO",
        ordem_descrescente: str = "N",
    ) -> dict:
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
            "ordenar_por": ordenar_por,
            "ordem_descrescente": ordem_descrescente,
            "filtrar_apenas_titulos_em_aberto": filtrar_apenas_titulos_em_aberto,
        }
        if filtrar_por_status:
            params["filtrar_por_status"] = filtrar_por_status
        if filtrar_por_data_de:
            params["filtrar_por_data_de"] = filtrar_por_data_de
        if filtrar_por_data_ate:
            params["filtrar_por_data_ate"] = filtrar_por_data_ate
        if filtrar_por_emissao_de:
            params["filtrar_por_emissao_de"] = filtrar_por_emissao_de
        if filtrar_por_emissao_ate:
            params["filtrar_por_emissao_ate"] = filtrar_por_emissao_ate
        if filtrar_cliente:
            params["filtrar_cliente"] = filtrar_cliente
        if filtrar_conta_corrente:
            params["filtrar_conta_corrente"] = filtrar_conta_corrente
        return await self.call(
            "financas/contareceber/", "ListarContasReceber", params, lista_vazia_ok=True
        )

    async def consultar_conta_receber(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_lancamento_omie:
            params["codigo_lancamento_omie"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        return await self.call("financas/contareceber/", "ConsultarContaReceber", params)

    async def incluir_conta_receber(
        self,
        codigo_cliente_fornecedor: int,
        data_vencimento: str,
        valor_documento: float,
        codigo_categoria: str,
        data_previsao: str,
        codigo_lancamento_integracao: Optional[str] = None,
        numero_documento: Optional[str] = None,
        data_emissao: Optional[str] = None,
        id_conta_corrente: Optional[int] = None,
        codigo_vendedor: Optional[int] = None,
        observacao: Optional[str] = None,
        numero_pedido: Optional[str] = None,
        numero_parcela: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "codigo_cliente_fornecedor": codigo_cliente_fornecedor,
            "data_vencimento": data_vencimento,
            "valor_documento": valor_documento,
            "codigo_categoria": codigo_categoria,
            "data_previsao": data_previsao,
        }
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if numero_documento:
            params["numero_documento"] = numero_documento
        if data_emissao:
            params["data_emissao"] = data_emissao
        if id_conta_corrente:
            params["id_conta_corrente"] = id_conta_corrente
        if codigo_vendedor:
            params["codigo_vendedor"] = codigo_vendedor
        if observacao:
            params["observacao"] = observacao
        if numero_pedido:
            params["numero_pedido"] = numero_pedido
        if numero_parcela:
            params["numero_parcela"] = numero_parcela
        return await self.call("financas/contareceber/", "IncluirContaReceber", params)

    async def alterar_conta_receber(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
        codigo_cliente_fornecedor: Optional[int] = None,
        data_vencimento: Optional[str] = None,
        valor_documento: Optional[float] = None,
        codigo_categoria: Optional[str] = None,
        data_previsao: Optional[str] = None,
        numero_documento: Optional[str] = None,
        data_emissao: Optional[str] = None,
        id_conta_corrente: Optional[int] = None,
        codigo_vendedor: Optional[int] = None,
        observacao: Optional[str] = None,
        numero_pedido: Optional[str] = None,
        numero_parcela: Optional[str] = None,
    ) -> dict:
        if not codigo_lancamento_omie and not codigo_lancamento_integracao:
            raise ValueError(
                "Informe codigo_lancamento_omie ou codigo_lancamento_integracao "
                "para identificar o título a alterar."
            )
        params: dict = {}
        if codigo_lancamento_omie:
            params["codigo_lancamento_omie"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if codigo_cliente_fornecedor:
            params["codigo_cliente_fornecedor"] = codigo_cliente_fornecedor
        if data_vencimento:
            params["data_vencimento"] = data_vencimento
        if valor_documento is not None:
            params["valor_documento"] = valor_documento
        if codigo_categoria:
            params["codigo_categoria"] = codigo_categoria
        if data_previsao:
            params["data_previsao"] = data_previsao
        if numero_documento:
            params["numero_documento"] = numero_documento
        if data_emissao:
            params["data_emissao"] = data_emissao
        if id_conta_corrente:
            params["id_conta_corrente"] = id_conta_corrente
        if codigo_vendedor:
            params["codigo_vendedor"] = codigo_vendedor
        if observacao:
            params["observacao"] = observacao
        if numero_pedido:
            params["numero_pedido"] = numero_pedido
        if numero_parcela:
            params["numero_parcela"] = numero_parcela
        return await self.call("financas/contareceber/", "AlterarContaReceber", params)

    async def lancar_recebimento(
        self,
        codigo_conta_corrente: int,
        valor: float,
        data: str,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
        desconto: float = 0.0,
        juros: float = 0.0,
        multa: float = 0.0,
        observacao: Optional[str] = None,
        conciliar_documento: str = "N",
    ) -> dict:
        params: dict = {
            "codigo_conta_corrente": codigo_conta_corrente,
            "valor": valor,
            "data": data,
            "desconto": desconto,
            "juros": juros,
            "multa": multa,
            "conciliar_documento": conciliar_documento,
        }
        # A baixa identifica o título por [codigo_lancamento], não por
        # [codigo_lancamento_omie] (esse é o nome usado só nos métodos de chave).
        if codigo_lancamento_omie:
            params["codigo_lancamento"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        if observacao:
            params["observacao"] = observacao
        return await self.call("financas/contareceber/", "LancarRecebimento", params)

    async def cancelar_recebimento(
        self,
        codigo_baixa: Optional[int] = None,
        codigo_baixa_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_baixa:
            params["codigo_baixa"] = codigo_baixa
        if codigo_baixa_integracao:
            params["codigo_baixa_integracao"] = codigo_baixa_integracao
        return await self.call("financas/contareceber/", "CancelarRecebimento", params)

    async def excluir_conta_receber(
        self,
        codigo_lancamento_omie: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        # ExcluirContaReceber usa [chave_lancamento] — diferente de
        # ConsultarContaReceber, que usa [codigo_lancamento_omie].
        if codigo_lancamento_omie:
            params["chave_lancamento"] = codigo_lancamento_omie
        if codigo_lancamento_integracao:
            params["codigo_lancamento_integracao"] = codigo_lancamento_integracao
        return await self.call("financas/contareceber/", "ExcluirContaReceber", params)

    # ------------------------------------------------------------------
    # Lançamentos em Conta Corrente — financas/contacorrentelancamentos/
    # ------------------------------------------------------------------

    async def listar_lancamentos_bancarios(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        codigo_conta_corrente: Optional[int] = None,
        data_lancamento_de: Optional[str] = None,
        data_lancamento_ate: Optional[str] = None,
        data_inclusao_de: Optional[str] = None,
        data_inclusao_ate: Optional[str] = None,
        ordem_descrescente: str = "S",
    ) -> dict:
        params: dict = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
            "cOrdemDecrescente": ordem_descrescente,
        }
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if data_lancamento_de:
            params["dtPagInicial"] = data_lancamento_de
        if data_lancamento_ate:
            params["dtPagFinal"] = data_lancamento_ate
        if data_inclusao_de:
            params["dDtIncDe"] = data_inclusao_de
        if data_inclusao_ate:
            params["dDtIncAte"] = data_inclusao_ate
        return await self.call(
            "financas/contacorrentelancamentos/", "ListarLancCC", params, lista_vazia_ok=True
        )

    async def consultar_lancamento_bancario(
        self,
        codigo_lancamento: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_lancamento:
            params["nCodLanc"] = codigo_lancamento
        if codigo_lancamento_integracao:
            params["cCodIntLanc"] = codigo_lancamento_integracao
        return await self.call("financas/contacorrentelancamentos/", "ConsultaLancCC", params)

    async def incluir_lancamento_bancario(
        self,
        codigo_conta_corrente: int,
        data_lancamento: str,
        valor: float,
        codigo_categoria: str,
        tipo_documento: str = "99999",
        numero_documento: Optional[str] = None,
        codigo_cliente: Optional[int] = None,
        codigo_conta_destino: Optional[int] = None,
        observacao: Optional[str] = None,
        codigo_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "cabecalho": {
                "nCodCC": codigo_conta_corrente,
                "dDtLanc": data_lancamento,
                "nValorLanc": valor,
            },
            "detalhes": {
                "cCodCateg": codigo_categoria,
                "cTipo": tipo_documento,
            },
        }
        if numero_documento:
            params["detalhes"]["cNumDoc"] = numero_documento
        if codigo_cliente:
            params["detalhes"]["nCodCliente"] = codigo_cliente
        if observacao:
            params["detalhes"]["cObs"] = observacao
        if codigo_conta_destino:
            params["transferencia"] = {"nCodCCDestino": codigo_conta_destino}
        if codigo_integracao:
            params["cCodIntLanc"] = codigo_integracao
        return await self.call("financas/contacorrentelancamentos/", "IncluirLancCC", params)

    async def excluir_lancamento_bancario(
        self,
        codigo_lancamento: Optional[int] = None,
        codigo_lancamento_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_lancamento:
            params["nCodLanc"] = codigo_lancamento
        if codigo_lancamento_integracao:
            params["cCodIntLanc"] = codigo_lancamento_integracao
        return await self.call("financas/contacorrentelancamentos/", "ExcluirLancCC", params)

    # ------------------------------------------------------------------
    # Contas Correntes e Extrato — geral/contacorrente/ e financas/extrato/
    # ------------------------------------------------------------------

    async def listar_contas_correntes(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
    ) -> dict:
        return await self.call(
            "geral/contacorrente/",
            "ListarResumoContasCorrentes",
            {"pagina": pagina, "registros_por_pagina": registros_por_pagina},
            lista_vazia_ok=True,
        )

    async def consultar_conta_corrente(
        self,
        codigo_conta_corrente: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
    ) -> dict:
        params: dict = {}
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if codigo_integracao:
            params["cCodIntCC"] = codigo_integracao
        return await self.call("geral/contacorrente/", "ConsultarContaCorrente", params)

    async def incluir_conta_corrente(
        self,
        descricao: str,
        tipo_conta_corrente: str,
        codigo_banco: Optional[str] = None,
        codigo_agencia: Optional[str] = None,
        numero_conta_corrente: Optional[str] = None,
        codigo_integracao: Optional[str] = None,
        saldo_inicial: Optional[float] = None,
        saldo_data: Optional[str] = None,
        valor_limite: Optional[float] = None,
        ocultar_do_fluxo: Optional[str] = None,
        ocultar_do_resumo: Optional[str] = None,
        observacao: Optional[str] = None,
    ) -> dict:
        """
        Cadastra uma conta corrente/bancária. tipo_conta_corrente segue a tabela
        de tipos do OMIE (ex: CC=conta corrente, CX=caixa, AC=aplicação) — use
        listar_tipos_conta_corrente para ver as opções válidas.
        """
        params: dict = {
            "descricao": descricao,
            "tipo_conta_corrente": tipo_conta_corrente,
        }
        if codigo_banco:
            params["codigo_banco"] = codigo_banco
        if codigo_agencia:
            params["codigo_agencia"] = codigo_agencia
        if numero_conta_corrente:
            params["numero_conta_corrente"] = numero_conta_corrente
        if codigo_integracao:
            params["cCodCCInt"] = codigo_integracao
        if saldo_inicial is not None:
            params["saldo_inicial"] = saldo_inicial
        if saldo_data:
            params["saldo_data"] = saldo_data
        if valor_limite is not None:
            params["valor_limite"] = valor_limite
        if ocultar_do_fluxo:
            params["nao_fluxo"] = ocultar_do_fluxo
        if ocultar_do_resumo:
            params["nao_resumo"] = ocultar_do_resumo
        if observacao:
            params["observacao"] = observacao
        return await self.call("geral/contacorrente/", "IncluirContaCorrente", params)

    async def alterar_conta_corrente(
        self,
        codigo_conta_corrente: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
        descricao: Optional[str] = None,
        tipo_conta_corrente: Optional[str] = None,
        codigo_banco: Optional[str] = None,
        codigo_agencia: Optional[str] = None,
        numero_conta_corrente: Optional[str] = None,
        saldo_inicial: Optional[float] = None,
        saldo_data: Optional[str] = None,
        valor_limite: Optional[float] = None,
        ocultar_do_fluxo: Optional[str] = None,
        ocultar_do_resumo: Optional[str] = None,
        observacao: Optional[str] = None,
    ) -> dict:
        if not codigo_conta_corrente and not codigo_integracao:
            raise ValueError(
                "Informe codigo_conta_corrente ou codigo_integracao para "
                "identificar a conta corrente a alterar."
            )
        params: dict = {}
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if codigo_integracao:
            params["cCodCCInt"] = codigo_integracao
        if descricao:
            params["descricao"] = descricao
        if tipo_conta_corrente:
            params["tipo_conta_corrente"] = tipo_conta_corrente
        if codigo_banco:
            params["codigo_banco"] = codigo_banco
        if codigo_agencia:
            params["codigo_agencia"] = codigo_agencia
        if numero_conta_corrente:
            params["numero_conta_corrente"] = numero_conta_corrente
        if saldo_inicial is not None:
            params["saldo_inicial"] = saldo_inicial
        if saldo_data:
            params["saldo_data"] = saldo_data
        if valor_limite is not None:
            params["valor_limite"] = valor_limite
        if ocultar_do_fluxo:
            params["nao_fluxo"] = ocultar_do_fluxo
        if ocultar_do_resumo:
            params["nao_resumo"] = ocultar_do_resumo
        if observacao:
            params["observacao"] = observacao
        return await self.call("geral/contacorrente/", "AlterarContaCorrente", params)

    async def excluir_conta_corrente(
        self,
        codigo_conta_corrente: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
    ) -> dict:
        if not codigo_conta_corrente and not codigo_integracao:
            raise ValueError(
                "Informe codigo_conta_corrente ou codigo_integracao para "
                "identificar a conta corrente a excluir."
            )
        params: dict = {}
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if codigo_integracao:
            params["cCodCCInt"] = codigo_integracao
        return await self.call("geral/contacorrente/", "ExcluirContaCorrente", params)

    async def consultar_extrato_bancario(
        self,
        data_inicio: str,
        data_fim: str,
        codigo_conta_corrente: Optional[int] = None,
        codigo_integracao_conta: Optional[str] = None,
        exibir_apenas_saldo: str = "N",
    ) -> dict:
        if not codigo_conta_corrente and not codigo_integracao_conta:
            raise ValueError(
                "Informe codigo_conta_corrente ou codigo_integracao_conta. "
                "Use listar_contas_correntes para obter o código."
            )
        params: dict = {
            "dPeriodoInicial": data_inicio,
            "dPeriodoFinal": data_fim,
            "cExibirApenasSaldo": exibir_apenas_saldo,
        }
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if codigo_integracao_conta:
            params["cCodIntCC"] = codigo_integracao_conta
        return await self.call("financas/extrato/", "ListarExtrato", params)

    # ------------------------------------------------------------------
    # Fluxo de Caixa e Resumo Financeiro — financas/caixa/, financas/resumo/
    # e financas/pesquisartitulos/
    # ------------------------------------------------------------------

    async def consultar_fluxo_caixa(self, ano: int, mes: int) -> dict:
        return await self.call(
            "financas/caixa/",
            "ListarOrcamentos",
            {"nAno": ano, "nMes": mes},
        )

    async def obter_resumo_financeiro(
        self,
        data: str,
        exibir_categoria: bool = False,
        apenas_resumo: bool = True,
    ) -> dict:
        return await self.call(
            "financas/resumo/",
            "ObterResumoFinancas",
            {
                "dDia": data,
                "lApenasResumo": apenas_resumo,
                "lExibirCategoria": exibir_categoria,
            },
        )

    async def listar_titulos_em_aberto(
        self,
        tipo: str,
        data: Optional[str] = None,
        codigo_cliente: Optional[int] = None,
        nome_cliente: Optional[str] = None,
        pagina: int = 1,
        registros_por_pagina: int = 20,
    ) -> dict:
        tipos = {"PAGAR": "P", "RECEBER": "R"}
        if tipo.upper() not in tipos:
            raise ValueError(f"tipo deve ser PAGAR ou RECEBER, recebido: {tipo!r}")
        params: dict = {
            "cTipo": tipos[tipo.upper()],
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
        }
        if data:
            params["dDia"] = data
        if codigo_cliente:
            params["nCodCliente"] = codigo_cliente
        if nome_cliente:
            params["cNomeCliente"] = nome_cliente
        return await self.call(
            "financas/resumo/", "ObterListaEmAberto", params, lista_vazia_ok=True
        )

    async def pesquisar_lancamentos_financeiros(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        natureza: Optional[str] = None,
        vencimento_de: Optional[str] = None,
        vencimento_ate: Optional[str] = None,
        emissao_de: Optional[str] = None,
        emissao_ate: Optional[str] = None,
        codigo_cliente: Optional[int] = None,
        codigo_conta_corrente: Optional[int] = None,
        status: Optional[str] = None,
    ) -> dict:
        params: dict = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
        }
        if natureza:
            naturezas = {"PAGAR": "P", "RECEBER": "R"}
            if natureza.upper() not in naturezas:
                raise ValueError(f"natureza deve ser PAGAR ou RECEBER, recebido: {natureza!r}")
            params["cNatureza"] = naturezas[natureza.upper()]
        if vencimento_de:
            params["dDtVencDe"] = vencimento_de
        if vencimento_ate:
            params["dDtVencAte"] = vencimento_ate
        if emissao_de:
            params["dDtEmisDe"] = emissao_de
        if emissao_ate:
            params["dDtEmisAte"] = emissao_ate
        if codigo_cliente:
            params["nCodCliente"] = codigo_cliente
        if codigo_conta_corrente:
            params["nCodCC"] = codigo_conta_corrente
        if status:
            params["cStatus"] = status
        return await self.call(
            "financas/pesquisartitulos/", "PesquisarLancamentos", params, lista_vazia_ok=True
        )

    # ------------------------------------------------------------------
    # Boletos de Contas a Receber — financas/contareceberboleto/
    # ------------------------------------------------------------------

    async def gerar_boleto(
        self,
        codigo_titulo: Optional[int] = None,
        codigo_titulo_integracao: Optional[str] = None,
    ) -> dict:
        """Gera o boleto de um título de contas a receber já existente."""
        params: dict = {}
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        if codigo_titulo_integracao:
            params["cCodIntTitulo"] = codigo_titulo_integracao
        return await self.call("financas/contareceberboleto/", "GerarBoleto", params)

    async def obter_boleto(
        self,
        codigo_titulo: Optional[int] = None,
        codigo_titulo_integracao: Optional[str] = None,
    ) -> dict:
        """Obtém o link de download do boleto de um título já gerado."""
        params: dict = {}
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        if codigo_titulo_integracao:
            params["cCodIntTitulo"] = codigo_titulo_integracao
        return await self.call("financas/contareceberboleto/", "ObterBoleto", params)

    async def prorrogar_boleto(
        self,
        nova_data_vencimento: str,
        codigo_titulo: Optional[int] = None,
        codigo_titulo_integracao: Optional[str] = None,
    ) -> dict:
        """Prorroga a data de vencimento do boleto de um título."""
        params: dict = {"dDtVenc": nova_data_vencimento}
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        if codigo_titulo_integracao:
            params["cCodIntTitulo"] = codigo_titulo_integracao
        return await self.call("financas/contareceberboleto/", "ProrrogarBoleto", params)

    async def cancelar_boleto(
        self,
        codigo_titulo: Optional[int] = None,
        codigo_titulo_integracao: Optional[str] = None,
    ) -> dict:
        """Cancela o boleto de um título de contas a receber."""
        params: dict = {}
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        if codigo_titulo_integracao:
            params["cCodIntTitulo"] = codigo_titulo_integracao
        return await self.call("financas/contareceberboleto/", "CancelarBoleto", params)

    # ------------------------------------------------------------------
    # PIX de Contas a Receber — financas/pix/
    # ------------------------------------------------------------------

    async def gerar_pix(
        self,
        codigo_integracao: str,
        valor: float,
        codigo_titulo: Optional[int] = None,
        codigo_conta_corrente: Optional[int] = None,
        url_notificacao: Optional[str] = None,
        codigo_cliente: Optional[int] = None,
        cnpj_cpf: Optional[str] = None,
    ) -> dict:
        """Gera uma cobrança PIX, associada ou não a um título de contas a receber."""
        params: dict = {
            "cCodIntPix": codigo_integracao,
            "vValor": valor,
        }
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        if codigo_conta_corrente:
            params["nIdConta"] = codigo_conta_corrente
        if url_notificacao:
            params["cUrlNotif"] = url_notificacao
        if codigo_cliente:
            params["nIdCliente"] = codigo_cliente
        if cnpj_cpf:
            params["cCnpjCpf"] = cnpj_cpf
        return await self.call("financas/pix/", "GerarPix", params)

    async def obter_pix(
        self,
        id_pix: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
        codigo_titulo: Optional[int] = None,
    ) -> dict:
        """Consulta os detalhes de uma cobrança PIX."""
        params: dict = {}
        if id_pix:
            params["nIdPix"] = id_pix
        if codigo_integracao:
            params["cCodIntPix"] = codigo_integracao
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        return await self.call("financas/pix/", "ObterPix", params)

    async def cancelar_pix(
        self,
        id_pix: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
        excluir: Optional[bool] = None,
    ) -> dict:
        """Cancela uma cobrança PIX. `excluir=True` remove o registro em vez de apenas cancelar."""
        params: dict = {}
        if id_pix:
            params["nIdPix"] = id_pix
        if codigo_integracao:
            params["cCodIntPix"] = codigo_integracao
        if excluir is not None:
            params["lDel"] = excluir
        return await self.call("financas/pix/", "CancelarPix", params)

    async def listar_pix(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        emissao_de: Optional[str] = None,
        emissao_ate: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Lista cobranças PIX geradas, com filtros por período de emissão e status."""
        params: dict = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
        }
        if emissao_de:
            params["dEmissaoDe"] = emissao_de
        if emissao_ate:
            params["dEmissaoAte"] = emissao_ate
        if status:
            params["cStatus"] = status
        return await self.call("financas/pix/", "ListarPix", params, lista_vazia_ok=True)

    async def listar_status_pix(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        emissao_de: Optional[str] = None,
        emissao_ate: Optional[str] = None,
        status: Optional[str] = None,
    ) -> dict:
        """Lista apenas o status das cobranças PIX geradas (consulta mais leve que listar_pix)."""
        params: dict = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
        }
        if emissao_de:
            params["dEmissaoDe"] = emissao_de
        if emissao_ate:
            params["dEmissaoAte"] = emissao_ate
        if status:
            params["cStatus"] = status
        return await self.call("financas/pix/", "ListarStatusPix", params, lista_vazia_ok=True)

    async def obter_status_pix(
        self,
        id_pix: Optional[int] = None,
        codigo_integracao: Optional[str] = None,
        codigo_titulo: Optional[int] = None,
    ) -> dict:
        """Consulta apenas o status de uma cobrança PIX específica."""
        params: dict = {}
        if id_pix:
            params["nIdPix"] = id_pix
        if codigo_integracao:
            params["cCodIntPix"] = codigo_integracao
        if codigo_titulo:
            params["nCodTitulo"] = codigo_titulo
        return await self.call("financas/pix/", "ObterStatusPix", params)

    async def gerar_qrcode_pix_estatico(
        self,
        codigo_conta_corrente: Optional[int] = None,
    ) -> dict:
        """Gera um QR Code PIX estático (sem valor fixo) para uma conta corrente."""
        params: dict = {}
        if codigo_conta_corrente:
            params["nIdConta"] = codigo_conta_corrente
        return await self.call("financas/pix/", "GerarQrCodePix", params)

    # ------------------------------------------------------------------
    # Movimentos Financeiros — financas/mf/
    # ------------------------------------------------------------------

    async def listar_movimentos_financeiros(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        ordenar_por: Optional[str] = None,
        incluir_dados_cadastrais: Optional[bool] = None,
        emissao_de: Optional[str] = None,
        emissao_ate: Optional[str] = None,
        vencimento_de: Optional[str] = None,
        vencimento_ate: Optional[str] = None,
        pagamento_de: Optional[str] = None,
        pagamento_ate: Optional[str] = None,
        codigo_cliente: Optional[int] = None,
        cnpj_cpf_cliente: Optional[str] = None,
        natureza: Optional[str] = None,
        status: Optional[str] = None,
        tipo_lancamento: Optional[str] = None,
    ) -> dict:
        """
        Consulta unificada de movimentos financeiros: títulos a pagar/receber,
        baixas e lançamentos de conta corrente num único resultado.
        natureza: PAGAR | RECEBER. tipo_lancamento segue a tabela do OMIE
        (ex: CP, CR, CPCR, BX, CC).
        """
        params: dict = {
            "nPagina": pagina,
            "nRegPorPagina": registros_por_pagina,
        }
        if ordenar_por:
            params["cOrdenarPor"] = ordenar_por
        if incluir_dados_cadastrais is not None:
            params["lDadosCad"] = incluir_dados_cadastrais
        if emissao_de:
            params["dDtEmisDe"] = emissao_de
        if emissao_ate:
            params["dDtEmisAte"] = emissao_ate
        if vencimento_de:
            params["dDtVencDe"] = vencimento_de
        if vencimento_ate:
            params["dDtVencAte"] = vencimento_ate
        if pagamento_de:
            params["dDtPagtoDe"] = pagamento_de
        if pagamento_ate:
            params["dDtPagtoAte"] = pagamento_ate
        if codigo_cliente:
            params["nCodCliente"] = codigo_cliente
        if cnpj_cpf_cliente:
            params["cCPFCNPJCliente"] = cnpj_cpf_cliente
        if natureza:
            naturezas = {"PAGAR": "P", "RECEBER": "R"}
            if natureza.upper() not in naturezas:
                raise ValueError(f"natureza deve ser PAGAR ou RECEBER, recebido: {natureza!r}")
            params["cNatureza"] = naturezas[natureza.upper()]
        if status:
            params["cStatus"] = status
        if tipo_lancamento:
            params["cTpLancamento"] = tipo_lancamento
        return await self.call("financas/mf/", "ListarMovimentos", params, lista_vazia_ok=True)

    # ------------------------------------------------------------------
    # Cadastros Auxiliares — geral/bancos/, geral/tipocc/, geral/dre/,
    # geral/tiposdoc/, geral/finaltransf/, geral/origemlancamento/,
    # geral/bandeiracartao/
    # ------------------------------------------------------------------

    async def listar_bancos(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        tipo: Optional[str] = None,
        nome: Optional[str] = None,
    ) -> dict:
        """Lista os bancos/instituições financeiras cadastrados no OMIE."""
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
        }
        if tipo:
            params["tipo"] = tipo
        if nome:
            params["nome"] = nome
        return await self.call("geral/bancos/", "ListarBancos", params, lista_vazia_ok=True)

    async def consultar_banco(self, codigo_banco: str) -> dict:
        """Consulta os detalhes de um banco/instituição financeira pelo código (ex: 341)."""
        return await self.call("geral/bancos/", "ConsultarBanco", {"codigo": codigo_banco})

    async def listar_tipos_conta_corrente(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        apenas_importado_api: Optional[str] = None,
        ordenar_por: Optional[str] = None,
        ordem_decrescente: Optional[str] = None,
    ) -> dict:
        """Lista os tipos de conta corrente aceitos pelo OMIE (ex: CC, CX, AC)."""
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
        }
        if apenas_importado_api:
            params["apenas_importado_api"] = apenas_importado_api
        if ordenar_por:
            params["ordenar_por"] = ordenar_por
        if ordem_decrescente:
            params["ordem_decrescente"] = ordem_decrescente
        return await self.call(
            "geral/tipocc/", "ListarTiposCC", params, lista_vazia_ok=True
        )

    async def listar_categorias_dre(self, apenas_contas_ativas: str = "S") -> dict:
        """Lista as contas do DRE (Demonstração de Resultado) usadas para categorizar lançamentos."""
        return await self.call(
            "geral/dre/",
            "ListarCadastroDRE",
            {"apenasContasAtivas": apenas_contas_ativas},
        )

    async def consultar_tipo_documento(self, codigo: str) -> dict:
        """Consulta um tipo de documento fiscal/financeiro pelo código."""
        return await self.call("geral/tiposdoc/", "ConsultarTipoDocumento", {"codigo": codigo})

    async def listar_tipos_documento(self, codigo: Optional[str] = None) -> dict:
        """Pesquisa os tipos de documento cadastrados no OMIE. Omita o código para listar todos."""
        params: dict = {}
        if codigo:
            params["codigo"] = codigo
        return await self.call(
            "geral/tiposdoc/", "PesquisarTipoDocumento", params, lista_vazia_ok=True
        )

    async def consultar_finalidade_transferencia(self, codigo_banco: str, codigo: str) -> dict:
        """Consulta uma finalidade de transferência (CNAB) de um banco específico."""
        return await self.call(
            "geral/finaltransf/",
            "ConsultarFinalTransf",
            {"banco": codigo_banco, "codigo": codigo},
        )

    async def listar_finalidades_transferencia(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        filtrar_por_banco: Optional[str] = None,
    ) -> dict:
        """Lista as finalidades de transferência (CNAB) aceitas, opcionalmente filtrando por banco."""
        params: dict = {
            "pagina": pagina,
            "registros_por_pagina": registros_por_pagina,
        }
        if filtrar_por_banco:
            params["filtrar_por_banco"] = filtrar_por_banco
        return await self.call(
            "geral/finaltransf/", "ListarFinalTransf", params, lista_vazia_ok=True
        )

    async def listar_origens_lancamento(self, codigo: Optional[str] = None) -> dict:
        """Lista as origens de lançamento financeiro cadastradas no OMIE."""
        params: dict = {}
        if codigo:
            params["codigo"] = codigo
        return await self.call(
            "geral/origemlancamento/", "ListarOrigem", params, lista_vazia_ok=True
        )

    async def listar_bandeiras_cartao(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
    ) -> dict:
        """Lista as bandeiras de cartão de crédito/débito aceitas pelo OMIE."""
        return await self.call(
            "geral/bandeiracartao/",
            "ListarBandeiras",
            {"nPagina": pagina, "nRegPorPagina": registros_por_pagina},
            lista_vazia_ok=True,
        )
