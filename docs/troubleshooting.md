# 🧯 Troubleshooting

## Erro: `DISCORD_TOKEN não configurado`
- Verifique o `.env` e garanta que `DISCORD_TOKEN` está definido.
- O bot interrompe a execução se essa variável não existir.

## Comandos não aparecem no Discord
- Verifique se `SYNC_COMMANDS` está `true` para sincronizar automaticamente.
- Para sincronizar manualmente, reinicie o bot com `SYNC_COMMANDS=true`.

## Falha ao carregar extensão
- Confira se a cog está listada em `config.py`.
- Consulte os logs de inicialização para ver a exceção.

## Banco de dados não inicializa
- O `init_db` é executado no boot e cria/atualiza o SQLite em `bestiario.db`.
- Se a aplicação falhar após alterações de schema, revise migrações em `database/migrations.py`.

## API/VTT não responde
- Garanta que o servidor ASGI esteja rodando a aplicação `api.routes:app`.
- Confirme se a URL do VTT está configurada em `VTT_API_URL` quando aplicável.
