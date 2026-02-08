# 🧩 Padrões de Código

## Organização
- **Cogs**: novos comandos devem viver em `cogs/` e ser registrados nas listas `extensions`/`optional_extensions` do `settings`. 
- **UI**: views/modais do Discord ficam em `ui/`.
- **Persistência**: toda alteração de banco passa por `database/` (schema, migrações e seeds).
- **API**: endpoints FastAPI e WebSocket estão em `api/routes.py`.

## Convenções recomendadas
- **Configuração centralizada**: utilize `config.Settings` ao invés de ler `os.getenv` diretamente em outras partes do código.
- **Logs**: prefira `logging` ao invés de `print` para eventos de runtime do bot.
- **Seeds**: dados iniciais devem ser adicionados via `database/seeds.py` ou arquivos em `data/seeds/`.

## Checklist de feature
1. Criar/alterar a cog relevante.
2. Atualizar `config.py` se a cog for nova.
3. Ajustar schema/migrações/seed se a feature depender de dados persistentes.
4. Testar localmente com `python bot.py`.
