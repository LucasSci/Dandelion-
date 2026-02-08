# 🛠️ Setup & Configuração

## Requisitos
- Python 3.8+
- Dependências em `requirements.txt`

## Instalação rápida

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Variáveis de ambiente (.env)
Crie um arquivo `.env` na raiz do projeto. As chaves mais usadas são:

```ini
DISCORD_TOKEN=seu_token
GEMINI_API_KEY=sua_chave_gemini
ROLL20_CAMPAIGN_URL=https://...
VTT_API_URL=https://...
DEFAULT_CHARACTER_THUMBNAIL_URL=https://...
LOG_LEVEL=INFO
HTTP_TIMEOUT_SECONDS=20
SYNC_COMMANDS=true
```

> Dica: `SYNC_COMMANDS=false` acelera o boot se você não quiser sincronizar os slash commands em cada execução.

## Inicialização

```bash
python bot.py
```

Ao iniciar, o bot prepara o banco e carrega as extensões configuradas.
