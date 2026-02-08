# Estratégia de Testes do Dandelion

## Objetivos
- Garantir estabilidade dos fluxos principais (fichas, combate, rolagens, quest/lore).
- Detectar regressões em regras e cálculos críticos.
- Automatizar validações em Pull Requests com cobertura mínima.

## Tipos de Teste

### 1) Testes Unitários
Foco em funções puras e regras do domínio.
- **Exemplos**: cálculo de atributos derivados, degradação de armadura, rolagens de dados.
- **Ferramentas**: `pytest` + `unittest` (compatível com a suíte atual).

### 2) Testes de Integração
Validam o fluxo entre módulos internos sem depender de Discord API externa.
- **Exemplos**: geração de loot, progressão de quests, exportação de ficha em JSON.
- **Ferramentas**: `pytest`, mocks de dependências externas.

### 3) Testes E2E (End-to-End)
Simulam o uso do bot por uma persona (mestre/jogador).
- **Exemplos**: criação de ficha → combate → exportação de log.
- **Ferramentas**: pipeline com mocks de Discord ou ambiente de staging.
- **Observação**: recomendados como etapa futura para garantir compatibilidade real com Discord.

## Fluxos Críticos Cobertos
1. **Cálculo de atributos derivados** (impacta combate e narrativa).
2. **Aplicação de dano e armadura** (impacta sobrevivência e balanceamento).
3. **Progressão de quests e geração de loot** (impacta campanhas e economia).
4. **Rolagens de dados** (base de todas as ações).

## Cobertura Mínima
O pipeline de CI exige **cobertura mínima de 30%** (configurado em `pytest.ini`).
O objetivo é elevar gradualmente conforme a base cresce.

## Execução Local
```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest
```

## CI em PRs
- Workflow dedicado em `.github/workflows/tests.yml`.
- Executa testes e valida cobertura mínima automaticamente.
