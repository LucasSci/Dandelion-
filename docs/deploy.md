# 🚀 Fluxo de Deploy

Este projeto não possui pipeline de deploy automatizado no repositório. O fluxo abaixo descreve a sequência típica para publicar uma versão:

## 1) Atualizar código
- Faça o pull da branch desejada.
- Revise mudanças de cogs e configurações.

## 2) Preparar ambiente
- Garanta o `.env` com os tokens e URLs necessários.
- Atualize dependências com `pip install -r requirements.txt`.

## 3) Inicializar serviços
- **Bot Discord**: execute `python bot.py`.
- **API/VTT (opcional)**: rode um servidor ASGI apontando para `api.routes:app`.

## 4) Verificações pós-deploy
- Confirme que os slash commands foram sincronizados (ou mantenha `SYNC_COMMANDS=false` para manter estabilidade).
- Verifique os logs para falhas ao carregar extensões e seeds.
