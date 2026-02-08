# 🪕 Dandelion - Bot de RPG para Discord

O **Dandelion** é um bot para Discord focado em campanhas de RPG (com temática de *The Witcher*), com automações de personagem, combate, bestiário, alquimia e narrativa assistida por IA. O projeto também inclui API/VTT, SDKs e um painel desktop local.

## 📚 Índice

- [Visão geral](#-visão-geral)
- [Funcionalidades implementadas](#-funcionalidades-implementadas)
- [Componentes do sistema](#-componentes-do-sistema)
- [Instalação](#-instalação)
- [Configuração (.env)](#-configuração-env)
- [Execução](#-execução)
- [Manual de uso (comandos principais)](#-manual-de-uso-comandos-principais)
- [API & VTT](#-api--vtt)
- [Observabilidade e logs](#-observabilidade-e-logs)
- [Documentação técnica](#-documentação-técnica)
- [Testes](#-testes)

## 👀 Visão geral

- **Discord Bot** com slash commands e views interativas.
- **Narrador IA** para descrição de cenas e suporte criativo.
- **Bestiário** com seeds e consulta inteligente (Monster Lore).
- **Combate e VTT** com grid, eventos e WebSocket.
- **API REST + GraphQL** para integração externa.
- **SDKs** simples (JS e Python).
- **Painel Desktop** para controle local do bot.

## 🚀 Funcionalidades implementadas

### Personagens & progressão
- Criação de ficha, pool de personagens, transferências entre jogadores e painel interativo de ficha.
- Atributos, armaduras por localização, modificadores de dano e aplicação de dano.
- Localização do personagem e controle de viagem.
- XP, nível, HP e ouro (comandos administrativos).

### Combate & VTT
- Criação de combate, entrada de jogadores, iniciativa e avanço de turno.
- Aplicação de status em jogadores e monstros.
- Movimentação de tokens no VTT e exportação de log de combate em Markdown.
- Grid procedimental (quadrado/hex), cálculo de custo de terreno e pathfinding.

### Bestiário & alquimia
- Seeds e imports de criaturas no banco local.
- Consulta a monstros com teste de **Monster Lore**.
- Geração de arte estilo Witcher (OpenAI) e busca automática de imagem de referência.
- Coleta de ingredientes por bioma, lista de receitas e criação de poções.

### Narrativa & conteúdo assistido por IA
- Narrador **/dandelion** com contexto de lore, memória de campanha e RAG.
- Geração de prompts visuais (Gemini) para arte de criaturas.

### Campanha, lore e mundo
- Diário de campanha com eventos, consequências, importações e edição.
- Banco de lore do mundo com CRUD e importação via `.txt`.
- Definição de bioma/clima e geração de ambientação por região.

### Quests, NPCs e rumores
- Criação manual e por IA de quests, publicação em fórum, atribuição e conclusão.
- Cadastro de NPCs, visualização de ficha e interação via IA.
- Sistema de rumores (adicionar, listar, sortear e marcar como usado).

### Economia, loja e inventário
- Loja com estoque, criação manual e geração por IA.
- Inventário do personagem e consumo de habilidades.

### Progressão social
- Facções, reputação, conquistas e legados.
- Comparação de builds e sugestão de pesos de atributos.

### Solo, utilitários e suporte
- Campanha solo e diário individual.
- Rolagem de dados por fórmula (ex.: `2d6+1`).
- Minijogo de Gwent.
- Relatórios de uso, feedback/NPS e abertura de tickets.
- Diagnóstico automático dos comandos (com relatório local).

## 🧩 Componentes do sistema

- **Bot Discord:** `bot.py` (cogs e UI do Discord).
- **API/VTT:** `api/routes.py` (FastAPI + GraphQL + WebSocket).
- **Regras do sistema:** `rpg_core/` e `witcher_rules.py`.
- **Infraestrutura e dados:** `database/`, `data/`, `infrastructure/`.
- **UI Discord:** `ui/` (views, modais e design system).
- **Painel Desktop:** `desktop_app.py` (controle local do bot).
- **SDKs:** `sdk/js` e `sdk/python`.

## 🛠️ Instalação

### Pré-requisitos

- Python **3.8+**
- Git (opcional, para clonar o repositório)

### Instalação rápida

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

O banco SQLite é inicializado automaticamente ao iniciar o bot.

## ⚙️ Configuração (.env)

Crie um arquivo `.env` na raiz do projeto. Principais variáveis:

```ini
# Discord
DISCORD_TOKEN=seu_token
SYNC_COMMANDS=true

# IA
OPENAI_API_KEY=sua_chave_openai
GEMINI_API_KEY=sua_chave_gemini

# Integrações
ROLL20_CAMPAIGN_URL=https://...
VTT_API_URL=https://...
DEFAULT_CHARACTER_THUMBNAIL_URL=https://...

# Logs e timeouts
LOG_LEVEL=INFO
HTTP_TIMEOUT_SECONDS=20

# Retenção/arquivo de dados
RETENTION_DAYS_SESSION_LOGS=30
RETENTION_DAYS_MEMORIA_CAMPANHA=180
RETENTION_DAYS_MENCOES_PERSONAGEM=180
ARCHIVE_ENABLED=true
ARCHIVE_AFTER_DAYS=90

# Localização
DEFAULT_LOCALE=pt-BR
DEFAULT_TIMEZONE=UTC
DEFAULT_CURRENCY=BRL
PRIORITY_LANGUAGES=pt-BR,en-US,es-ES

# API (REST/GraphQL)
DANDELION_API_KEY=dev-secret
DANDELION_RATE_LIMIT=60
DANDELION_RATE_LIMIT_WINDOW=60
```

## ▶️ Execução

### Bot Discord

```bash
python bot.py
```

### Painel desktop (controle local)

```bash
python desktop_app.py
```

### API/VTT (FastAPI)

```bash
uvicorn api.routes:app --host 0.0.0.0 --port 8000
```

## 📘 Manual de uso (comandos principais)

> Dica: use `/status` para checar saúde do bot e banco.

### Personagens & progressão
- `/criar_ficha`, `/mestre_criar`, `/ficha`, `/listar_fichas`, `/ficha_exportar`
- `/assumir_personagem`, `/devolver_ficha`, `/mestre_vincular`
- `/atributo_definir`, `/atributo_listar`
- `/armadura_definir`, `/armadura_modificador`, `/receber_dano`
- `/localizacao`, `/viajar`
- `/mestre_add_xp`, `/mestre_levelup`, `/mestre_leveldown`, `/mestre_ouro`

### Combate & VTT
- `/combate_criar`, `/combate_adicionar`, `/combate_entrar`, `/combate_iniciar`
- `/combate_status_jogador`, `/combate_status_monstro`, `/combate_mover`
- `/combate_exportar`

### Bestiário & alquimia
- `/ver` (consulta de criatura), `/gerar_imagem`
- `/forage`, `/alquimia_ingredientes`, `/alquimia_receitas`, `/alquimia_criar`

### Campanha, lore e mundo
- `/diario_campanha ver`, `/diario_campanha adicionar`, `/diario_campanha consequencia`
- `/diario_campanha importar_txt`, `/diario_campanha editar`, `/diario_campanha apagar`, `/diario_campanha limpar_tudo`
- `/lore ver`, `/lore adicionar`, `/lore importar_txt`, `/lore editar`, `/lore apagar`, `/lore limpar_tudo`
- `/mundo definir_bioma`, `/mundo ambientacao`

### Narrativa, quests e NPCs
- `/dandelion` (narrador IA)
- `/quest_criar`, `/quest_gerar`, `/quest_publicar`, `/quest_atribuir`, `/quest_concluir`
- `/memoria_importar` (upload de TXT para lore de campanha)
- `/npc_criar`, `/npc_ver`, `/npc_falar`
- `/rumor_adicionar`, `/rumor_listar`, `/rumor_sortear`, `/rumor_usar`

### Economia, inventário e habilidades
- `/loja`, `/loja_adicionar`, `/loja_gerar`, `/loja_estoque`, `/loja_remover`
- `/inventario`, `/usar_habilidade`

### Progressão social
- `/faccao_criar`, `/faccao_listar`
- `/reputacao_definir`, `/reputacao_ver`
- `/conquista_criar`, `/conquista_dar`, `/conquistas_ver`
- `/legado_adicionar`, `/legado_ver`
- `/comparar_builds`, `/atributos_sugerir`

### Solo, utilitários e suporte
- `/onboarding`, `/dashboard`
- `/rolar`
- `/gwent`
- `/roadmap`
- `/feedback`, `/nps`, `/satisfacao`, `/ticket_abrir`, `/relatorio_uso`
- `/testar_comandos` (diagnóstico interno)

## 🔌 API & VTT

- REST em `/v1/*` e GraphQL em `/v1/graphql`.
- Autenticação via `X-API-Key` ou `Authorization: Bearer <API_KEY>`.
- WebSocket do VTT em `/ws/vtt`.
- Documentação OpenAPI em `/docs` e `/openapi.json`.

Veja mais em **[`docs/API.md`](docs/API.md)**.

## 📈 Observabilidade e logs

- Logs estruturados e métricas Prometheus em `/metrics` quando a API estiver ativa.
- Instrumentação com OpenTelemetry (configurada via variáveis `OTEL_EXPORTER_*`).

## 🧠 Documentação técnica

- **Arquitetura:** `docs/architecture.md`
- **Setup:** `docs/setup.md`
- **Deploy:** `docs/deploy.md`
- **Padrões de código:** `docs/code-standards.md`
- **Troubleshooting:** `docs/troubleshooting.md`
- **FAQ:** `docs/faq.md`

## ✅ Testes

```bash
pytest
```

Para detalhes de estratégia de testes, veja `docs/TESTING_STRATEGY.md`.
