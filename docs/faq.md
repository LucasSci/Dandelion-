# ❓ FAQ

## O bot funciona sem a chave do Gemini?
Sim. A chave do Gemini é opcional e só é usada para comandos de IA. Sem ela, os recursos de geração vão responder com mensagem de configuração faltando.

## Como faço para desativar a sincronização de comandos?
Defina `SYNC_COMMANDS=false` no `.env`. Isso evita a sincronização automática no boot.

## Posso rodar apenas a API/VTT sem o bot?
Sim. A aplicação FastAPI está em `api/routes.py` e pode ser servida separadamente por um servidor ASGI.

## Onde ficam os dados do banco?
O SQLite é criado como `bestiario.db` na raiz do projeto (a partir do `database/connection.py`).

## Como adicionar novos dados de bestiário?
Crie SQLs em `data/seeds/` ou adicione entradas em `database/seeds.py`.
