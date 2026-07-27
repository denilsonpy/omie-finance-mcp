FROM python:3.12-slim

WORKDIR /app

# Only the files pip needs to resolve and install the package — keeps the
# build cache valid across source edits that don't touch dependencies.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 omiefinancemcp
USER omiefinancemcp

# Runs as one persistent HTTP service (MCP_TRANSPORT=streamable-http, see
# docker-compose.yml / server.py) — clients connect over HTTP, they don't
# spawn this container themselves.
EXPOSE 8020

ENTRYPOINT ["omie-finance-mcp"]
