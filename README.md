# omie-finance-mcp

Um servidor [MCP](https://modelcontextprotocol.io) que expõe a API financeira do
**OMIE ERP** como ferramentas para agentes de IA. Em vez de navegar pelo painel do
OMIE ou montar chamadas HTTP manualmente, um assistente (Claude, ou qualquer outro
cliente compatível com MCP) passa a conseguir consultar títulos, lançar
pagamentos/recebimentos, gerar boletos e PIX, e ler o fluxo de caixa — tudo a
partir de um pedido em linguagem natural.

Exemplos do tipo de pedido que o assistente consegue resolver sozinho:

> "Quais contas a pagar vencem essa semana?"
> "Gera um boleto pro título 4821 com vencimento pro dia 10"
> "Qual o saldo da conta corrente principal hoje?"
> "Cadastra a Fulana Ltda como fornecedora, CNPJ 12.345.678/0001-99"

## Como o projeto é organizado

- `client.py` — cliente HTTP puro para a API do OMIE. Cada operação (`listar_contas_pagar`,
  `gerar_pix`, etc.) é um método nomeado, então dá pra usar essa classe fora do
  contexto do MCP também, se precisar.
- `auth.py` — só entra em jogo no modo servidor HTTP (ver abaixo): resolve qual
  credencial OMIE atende cada requisição.
- `server.py` — monta o servidor MCP (via [FastMCP](https://github.com/modelcontextprotocol/python-sdk))
  e registra as ferramentas.
- `tools/` — um arquivo por área do OMIE (contas a pagar, PIX, cadastros...),
  cada um só traduzindo argumentos da ferramenta para uma chamada do `client.py`.

Duas formas de rodar, dependendo do uso:

| | Modo local (stdio) | Modo servidor (HTTP) |
|---|---|---|
| Para quem | Uso pessoal, uma credencial OMIE | Vários usuários/clientes, cada um com a própria conta OMIE |
| Como sobe | `uvx`, ou o próprio Claude Desktop spawna o processo | Container Docker de vida longa |
| Credencial | Fixa, via variável de ambiente | Por requisição, via HTTP Basic Auth |

## Requisitos

- Python 3.12 ou superior
- Uma `app_key`/`app_secret` do OMIE (**Configurações → API → Aplicações**, dentro do OMIE)
- Para o modo local: [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Para o modo servidor: Docker + Docker Compose

---

## Modo local

Ideal quando é só você usando, com uma única conta OMIE.

**Sem clonar nada**, direto do GitHub:

```bash
OMIE_APP_KEY=sua_key OMIE_APP_SECRET=seu_secret \
  uvx --from git+https://github.com/denilsonpy/omie-finance-mcp omie-finance-mcp
```

Se preferir não repetir as credenciais toda vez, salve-as em
`~/.config/omie-finance-mcp/.env`:

```bash
mkdir -p ~/.config/omie-finance-mcp
printf 'OMIE_APP_KEY=sua_key\nOMIE_APP_SECRET=seu_secret\n' > ~/.config/omie-finance-mcp/.env

uvx --from git+https://github.com/denilsonpy/omie-finance-mcp omie-finance-mcp
```

**Clonando o repositório** (útil se for mexer no código):

```bash
git clone https://github.com/denilsonpy/omie-finance-mcp
cd omie-finance-mcp
cp .env.example .env   # preencha OMIE_APP_KEY e OMIE_APP_SECRET
uv run omie-finance-mcp
```

### Registrando no Claude Desktop

Edite o arquivo de configuração —
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`,
**Linux:** `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omie-finance-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/denilsonpy/omie-finance-mcp", "omie-finance-mcp"],
      "env": {
        "OMIE_APP_KEY": "sua_app_key",
        "OMIE_APP_SECRET": "seu_app_secret"
      }
    }
  }
}
```

**No Windows via WSL**, o Claude Desktop roda fora do Linux, então o jeito
confiável é um script wrapper. Dentro do WSL:

```bash
mkdir -p ~/.config/omie-finance-mcp
printf 'OMIE_APP_KEY=sua_app_key\nOMIE_APP_SECRET=seu_app_secret\n' > ~/.config/omie-finance-mcp/.env

cat > ~/omie-finance-mcp-run.sh << 'EOF'
#!/bin/bash
set -e
export $(grep -v '^#' ~/.config/omie-finance-mcp/.env | xargs)
exec uvx --from git+https://github.com/denilsonpy/omie-finance-mcp omie-finance-mcp
EOF
chmod +x ~/omie-finance-mcp-run.sh
```

E em `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omie-finance-mcp": {
      "command": "wsl",
      "args": ["/home/SEU_USUARIO/omie-finance-mcp-run.sh"]
    }
  }
}
```

(troque `SEU_USUARIO` pelo valor de `whoami` dentro do WSL)

---

## Modo servidor (Docker, multi-cliente)

Aqui a lógica muda: em vez de um processo por usuário com uma credencial fixa,
sobe **um único servidor HTTP** que várias pessoas/clientes compartilham — e cada
um usa a própria conta OMIE.

Isso só funciona porque a autenticação é **por requisição**: o servidor não
guarda `app_key`/`app_secret` nenhum. Cada chamada MCP chega com HTTP Basic Auth
(usuário = `app_key`, senha = `app_secret`), e é essa credencial — validada pelo
próprio OMIE, não por um cadastro paralelo — que decide qual conta aquela
chamada enxerga. Um cliente não tem como acessar dados de outro porque
literalmente não tem a chave dele.

```bash
git clone https://github.com/denilsonpy/omie-finance-mcp
cd omie-finance-mcp
cp .env.example .env   # não preencha OMIE_APP_KEY/SECRET aqui, ver acima
docker compose up -d --build
```

Por padrão sobe em `http://localhost:8020/mcp`. `docker compose down` para;
`restart: unless-stopped` no compose já garante que volta sozinho depois de um
reboot.

### Antes de expor isso na internet

Duas coisas que precisam estar certas:

1. **TLS na frente.** Basic Auth só ofusca em base64 — sem HTTPS, a credencial de
   qualquer cliente pode ser capturada em trânsito. Coloque um reverse proxy
   (Caddy, nginx) com certificado válido antes de aceitar tráfego público; dá
   pra conseguir HTTPS sem nem ter domínio próprio usando
   [sslip.io](https://sslip.io). Numa rede fechada (VPN, LAN), Basic Auth sozinho
   já resolve.
2. **`MCP_ALLOWED_HOSTS`.** O SDK do MCP tem proteção contra DNS rebinding e, por
   padrão, só aceita requisições cujo `Host` seja `localhost`. Atrás de um
   domínio/IP público, declare esse hostname na variável (ver `.env.example`) —
   senão toda chamada externa recebe `421`.

### Cada cliente se conecta com a própria credencial

```bash
# gera o header a partir do app_key/app_secret do cliente
echo -n "APP_KEY_DO_CLIENTE:APP_SECRET_DO_CLIENTE" | base64
```

```bash
claude mcp add --transport http omie-finance-mcp https://seu-servidor/mcp \
  --header "Authorization: Basic <valor_gerado_acima>"
```

ou equivalente em `.mcp.json` / `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "omie-finance-mcp": {
      "type": "http",
      "url": "https://seu-servidor/mcp",
      "headers": { "Authorization": "Basic <valor_gerado_acima>" }
    }
  }
}
```

---

## Ferramentas disponíveis

54 ferramentas ao todo, agrupadas por área:

### Cadastros

| Ferramenta | O que faz |
|---|---|
| `listar_fornecedores` | Fornecedores cadastrados, com filtro por nome/CNPJ |
| `consultar_fornecedor` | Detalhes de um fornecedor (código ou CNPJ) |
| `incluir_fornecedor` | Cadastra um fornecedor novo |
| `alterar_fornecedor` | Atualiza um fornecedor existente |
| `listar_bancos` | Bancos/instituições financeiras conhecidas pelo OMIE |
| `consultar_banco` | Um banco específico, pelo código |
| `listar_tipos_conta_corrente` | Tipos de conta aceitos ao cadastrar uma conta corrente |
| `listar_categorias_dre` | Categorias do DRE usadas para classificar lançamentos |
| `consultar_tipo_documento` | Um tipo de documento fiscal, pelo código |
| `listar_tipos_documento` | Tipos de documento cadastrados |
| `consultar_finalidade_transferencia` | Finalidade de transferência (CNAB) de um banco |
| `listar_finalidades_transferencia` | Finalidades de transferência (CNAB) disponíveis |
| `listar_origens_lancamento` | Origens de lançamento financeiro |
| `listar_bandeiras_cartao` | Bandeiras de cartão aceitas |

### Contas a Pagar

| Ferramenta | O que faz |
|---|---|
| `listar_contas_pagar` | Filtra por status, período, fornecedor |
| `consultar_conta_pagar` | Detalhes de um título específico |
| `incluir_conta_pagar` | Lança um novo título |
| `alterar_conta_pagar` | Edita um título existente |
| `lancar_pagamento` | Registra a baixa (pagamento) de um título |
| `cancelar_pagamento_conta_pagar` | Estorna uma baixa já registrada |
| `excluir_conta_pagar` | Remove um título em aberto |

### Contas a Receber

| Ferramenta | O que faz |
|---|---|
| `listar_contas_receber` | Filtra por status, período, cliente |
| `consultar_conta_receber` | Detalhes de um título específico |
| `incluir_conta_receber` | Lança um novo título |
| `alterar_conta_receber` | Edita um título existente |
| `lancar_recebimento` | Registra a baixa (recebimento) de um título |
| `cancelar_recebimento` | Estorna uma baixa já registrada |
| `excluir_conta_receber` | Remove um título em aberto |

### Cobranças — Boleto e PIX

| Ferramenta | O que faz |
|---|---|
| `gerar_boleto` | Emite o boleto de um título já lançado |
| `obter_boleto` | Link de download de um boleto já emitido |
| `prorrogar_boleto` | Muda a data de vencimento de um boleto |
| `cancelar_boleto` | Cancela o boleto de um título |
| `gerar_pix` | Cria uma cobrança PIX, associada a um título ou avulsa |
| `obter_pix` | Detalhes de uma cobrança PIX |
| `cancelar_pix` | Cancela uma cobrança PIX |
| `listar_pix` | Cobranças PIX por período/status |
| `listar_status_pix` | Igual acima, versão enxuta (só status) |
| `obter_status_pix` | Status de uma cobrança específica |
| `gerar_qrcode_pix_estatico` | QR Code PIX sem valor fixo, pra uma conta corrente |

### Movimento bancário

| Ferramenta | O que faz |
|---|---|
| `listar_contas_correntes` | Contas correntes/bancárias cadastradas |
| `consultar_conta_corrente` | Detalhes de uma conta específica |
| `incluir_conta_corrente` | Cadastra uma conta corrente nova |
| `alterar_conta_corrente` | Edita uma conta existente |
| `excluir_conta_corrente` | Remove uma conta corrente |
| `consultar_extrato_bancario` | Extrato de uma conta num período |
| `listar_lancamentos_bancarios` | Transações manuais na conta corrente |
| `consultar_lancamento_bancario` | Detalhes de um lançamento bancário |
| `incluir_lancamento_bancario` | Registra um lançamento manual (débito/crédito) |
| `excluir_lancamento_bancario` | Remove um lançamento bancário |

### Visão financeira

| Ferramenta | O que faz |
|---|---|
| `consultar_fluxo_caixa` | Previsto vs. realizado por categoria, num mês |
| `obter_resumo_financeiro` | Totais consolidados numa data de referência |
| `listar_titulos_em_aberto` | Títulos ainda não liquidados, a pagar ou a receber |
| `pesquisar_lancamentos_financeiros` | Busca unificada entre pagar e receber |
| `listar_movimentos_financeiros` | Títulos, baixas e lançamentos de conta corrente, numa visão só |

---

## Estrutura

```
omie-finance-mcp/
├── src/omie_finance_mcp/
│   ├── client.py
│   ├── auth.py
│   ├── server.py
│   └── tools/
│       ├── suppliers.py
│       ├── accounts_payable.py
│       ├── accounts_receivable.py
│       ├── bank_accounts.py
│       ├── bank_transactions.py
│       ├── receivable_boletos.py
│       ├── receivable_pix.py
│       ├── cash_flow.py
│       ├── financial_movements.py
│       └── finance_registries.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

## Licença

MIT — veja [LICENSE](LICENSE).
