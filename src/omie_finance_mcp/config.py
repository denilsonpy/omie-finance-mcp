"""Configuração do servidor, lida do ambiente e de arquivos .env.

Duas origens de .env, na ordem que o uso via uvx exige:
`~/.config/omie-mcp/.env` como padrão do usuário e o `.env` do diretório
atual sobrescrevendo-o. Variáveis já presentes no ambiente vencem os dois —
é assim que o `environment:` do docker-compose e o `env` da configuração de
um cliente MCP mandam sem precisar de arquivo nenhum.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_USER_ENV_FILE = Path.home() / ".config" / "omie-mcp" / ".env"


class Settings(BaseSettings):
    # O último arquivo da tupla tem prioridade (regra do pydantic-settings).
    model_config = SettingsConfigDict(
        env_file=(_USER_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Credenciais do OMIE do próprio servidor. Só fazem sentido em modo stdio,
    # onde o cliente sobe este processo e há um único usuário por processo. Em
    # modo HTTP cada requisição traz a credencial de quem chamou (ver auth.py)
    # e estas ficam sem uso — por isso são opcionais.
    omie_app_key: str | None = None
    omie_app_secret: str | None = None

    # "stdio" (padrão) para clientes que sobem este processo diretamente
    # (uvx, Claude Desktop). "streamable-http" para rodar como serviço HTTP
    # persistente e multi-tenant (ver docker-compose.yml).
    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8020

    # Valores de Host aceitos pela proteção anti-DNS-rebinding do SDK do MCP,
    # separados por vírgula (ex: "mcp.exemplo.com,203.0.113.7:8020"; um host
    # sem porta casa qualquer porta). Vazio (o padrão) desliga essa checagem,
    # que é o que um servidor acessado remotamente precisa: o SDK a liga
    # sozinho para localhost e aí responde 421 a toda requisição cujo Host não
    # seja 127.0.0.1/localhost. Quem controla acesso aqui é a credencial do
    # OMIE, não o header Host.
    mcp_allowed_hosts: str = ""

    # Origins extras aceitos além dos derivados de MCP_ALLOWED_HOSTS. Só têm
    # efeito quando MCP_ALLOWED_HOSTS está preenchido (é ele que liga a
    # checagem).
    mcp_allowed_origins: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Configuração do processo, lida uma única vez.

    Em cache porque o lifespan e o main() precisam da mesma instância, e
    reler os .env a cada acesso deixaria a configuração mudar debaixo de um
    servidor já em execução.
    """
    return Settings()


def parse_csv(raw: str) -> list[str]:
    """Quebra um valor separado por vírgula, descartando vazios e espaços."""
    return [item.strip() for item in raw.split(",") if item.strip()]
