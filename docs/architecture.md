# 🧭 Arquitetura

## Visão geral

O Dandelion é composto por um bot Discord, uma camada de persistência SQLite, módulos de regras e um serviço HTTP/WebSocket opcional para integração com VTT.

## Componentes principais

### Bot Discord
- **Ponto de entrada**: `bot.py` instancia o `DandelionBot`, inicializa o banco e carrega as extensões/cogs. O bot mantém sessão HTTP e conexão persistente com SQLite para atender comandos e integrações. 
- **Configuração**: `config.py` centraliza as variáveis de ambiente (tokens, URLs e flags). 

### Cogs e UI
- **Cogs**: ficam em `cogs/` e são carregadas pelo `DandelionBot` com base nas listas `extensions` e `optional_extensions` do settings. 
- **UI**: componentes de interface (views/modais) para Discord estão em `ui/`.

### Persistência
- **SQLite**: o banco é inicializado via `database.init_db`, que aplica schema, migrações e seeds na inicialização. 
- **Seeds**: dados iniciais e bestiário ficam em `data/seeds/` e são aplicados via `database/seeds.py`.

### API/VTT
- **FastAPI**: `api/routes.py` expõe endpoints HTTP para rolagens e atualização de combate, além de WebSocket para eventos de VTT.
- **Motor de grid**: `vtt_engine/grid_system.py` fornece geração de mapas, custos de terreno e pathfinding.

## Fluxo de dados (alto nível)
1. Usuário aciona um slash command no Discord.
2. O `DandelionBot` encaminha para a cog correspondente.
3. A cog aplica regras (ex.: `witcher_rules.py`) e lê/escreve no SQLite.
4. (Opcional) eventos de combate/mapa podem ser enviados/recebidos via API/VTT.
