# Modules

This directory groups core domains into dedicated modules. Each module exposes
its **contracts** first (interfaces/APIs) so implementations can follow a stable
boundary.

## Módulos-chave

- **Analytics**: coleta, agregação e consulta de eventos/indicadores.
- **Automação**: definição e execução de fluxos, regras e agendamentos.
- **Integrações**: conectores externos, sincronização e webhooks.
- **Admin**: gestão de usuários, permissões e configurações globais.

## Contratos antes de código

Each module owns a `contracts.py` file that defines its public interfaces. These
contracts must remain implementation-agnostic and act as the internal API.
Implementations should be created in separate files (e.g. `services.py`) only
after contracts are reviewed and accepted.
