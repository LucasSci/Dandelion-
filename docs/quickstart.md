# ⚡ Guia rápido para novos contribuidores

## 1) Onboarding rápido
1. Clone o repositório.
2. Crie um virtualenv e instale dependências.
3. Configure o `.env` com o `DISCORD_TOKEN`.
4. Rode `python bot.py` e confirme que o bot ficou online.

## 2) Onde mexer primeiro
- **Comandos**: `cogs/` (ex.: personagens, combate, inventário).
- **UI do Discord**: `ui/` (views e modais).
- **Regras**: `witcher_rules.py` e `rpg_core/`.
- **API/VTT**: `api/routes.py` e `vtt_engine/`.

## 3) Criando um novo comando
1. Crie uma nova cog em `cogs/` seguindo o padrão das existentes.
2. Registre a extensão em `config.py`.
3. Reinicie o bot (com `SYNC_COMMANDS=true` se quiser sincronizar).

## 4) Dados iniciais
- Seeds ficam em `data/seeds/`.
- Seeds internas e registros base estão em `database/seeds.py`.

## 5) Debug rápido
- Acompanhe os logs no console do bot.
- Use `LOG_LEVEL=DEBUG` para mais detalhes.
