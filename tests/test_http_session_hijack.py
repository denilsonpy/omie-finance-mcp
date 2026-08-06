"""A credencial de cada chamada é a de quem fez AQUELA requisição — nunca a de
quem abriu a sessão.

Este é o teste que distingue resolver a credencial por requisição de resolvê-la
num ContextVar setado pelo middleware. Um ContextVar sobrevive congelado no
valor da requisição de `initialize` (o loop da sessão MCP roda numa task criada
ali), então uma chamada posterior na mesma sessão executaria com a credencial
de quem abriu a sessão, e não com a de quem fez a chamada. Como cada cliente
normalmente abre a própria sessão com a própria credencial, o erro não aparece
no uso comum — mas aparece aqui, e é uma escalada entre tenants: com um session
id vazado, quem apresentasse a própria credencial válida operaria na conta OMIE
do dono da sessão.
"""

import json

import anyio
import httpx

from omie_finance_mcp.auth import APP_KEY_HEADER, APP_SECRET_HEADER

from .conftest import basic_header

DONO_DA_SESSAO = ("3333333333333", "segredo-do-dono")
INTRUSO = ("4444444444444", "segredo-do-intruso")

_ACCEPT = "application/json, text/event-stream"
_PROTOCOL_VERSION = "2025-06-18"


def _payload(response: httpx.Response) -> dict:
    """Corpo de uma resposta do streamable-http, seja JSON ou SSE."""
    if response.headers.get("content-type", "").startswith("application/json"):
        return response.json()
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[len("data:") :].strip())
    raise AssertionError(f"resposta sem payload: {response.text!r}")


async def _initialize(http: httpx.AsyncClient, base_url: str, credencial) -> str:
    response = await http.post(
        f"{base_url}/mcp",
        headers={"Accept": _ACCEPT, "Authorization": basic_header(*credencial)},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": _PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "teste", "version": "0"},
            },
        },
    )
    assert response.status_code == 200, response.text
    session_id = response.headers["mcp-session-id"]

    notified = await http.post(
        f"{base_url}/mcp",
        headers={
            "Accept": _ACCEPT,
            "Authorization": basic_header(*credencial),
            "mcp-session-id": session_id,
        },
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert notified.status_code in (200, 202), notified.text
    return session_id


async def _call_tool(http, base_url: str, session_id: str, headers: dict[str, str]) -> dict:
    response = await http.post(
        f"{base_url}/mcp",
        headers={"Accept": _ACCEPT, "mcp-session-id": session_id, **headers},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "listar_contas_correntes", "arguments": {}},
        },
    )
    return response


def test_chamada_usa_a_credencial_da_propria_requisicao(http_server):
    async def run():
        async with httpx.AsyncClient(timeout=30) as http:
            session_id = await _initialize(http, http_server, DONO_DA_SESSAO)
            response = await _call_tool(
                http,
                http_server,
                session_id,
                {APP_KEY_HEADER: INTRUSO[0], APP_SECRET_HEADER: INTRUSO[1]},
            )
            assert response.status_code == 200, response.text
            resultado = _payload(response)["result"]
            return json.loads(resultado["content"][0]["text"])

    usado = anyio.run(run)
    assert usado["app_key_usada"] == INTRUSO[0]
    # A credencial de quem abriu a sessão não pode ser reaproveitada por outra
    # requisição só porque ela reusou o session id.
    assert usado["app_key_usada"] != DONO_DA_SESSAO[0]


def test_chamada_sem_credencial_na_sessao_de_outro_recebe_401(http_server):
    async def run():
        async with httpx.AsyncClient(timeout=30) as http:
            session_id = await _initialize(http, http_server, DONO_DA_SESSAO)
            return await _call_tool(http, http_server, session_id, {})

    response = anyio.run(run)
    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"
