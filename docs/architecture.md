# Arquitetura e responsabilidades dos módulos

## Visão geral
Este repositório segue um fluxo típico de bot Discord: **cogs** recebem comandos e delegam para serviços, que orquestram regras de negócio e dependências. Persistência e integrações externas ficam em **infra**. Regras de domínio permanecem isoladas em módulos próprios.

## Mapeamento de módulos

| Camada | Módulo | Responsabilidade principal |
| --- | --- | --- |
| Apresentação | `cogs/` | Comandos do Discord, orquestração de respostas e validações de UI. |
| Apresentação | `ui/` | Views e componentes de interação (embeds, botões, modais). |
| Aplicação | `application/services/` | Casos de uso e fluxos de campanha (ex.: campanha solo). |
| Aplicação | `application/models/` | Objetos de transporte de dados entre camadas. |
| Aplicação | `application/ports/` | Interfaces (ports) para integrações externas e repositórios. |
| Domínio | `rpg_core/` | Regras e cálculos de sistema (atributos, stats derivados, schemas). |
| Infra | `infrastructure/repositories/` | Adaptações para persistência em banco/SQLite. |
| Infra | `data/repositories/` | Implementações concretas de acesso ao banco (SQL assíncrono). |
| Infra | `database/` | Conexão, migrações e schema do banco. |
| Suporte | `utils/` | Utilitários comuns (ex.: parsing de dados/rolagens). |
| Suporte | `scripts/` | Scripts auxiliares e tarefas pontuais. |

## Separação de responsabilidades

- **Aplicação**: consolida regras de fluxo (como avanço de campanha) e expõe resultados prontos para a camada de apresentação.
- **Infra**: concentra acesso a banco e integrações externas; a aplicação depende apenas de interfaces (`ports`).
- **Domínio**: mantém regras de jogo isoladas para reutilização.

## Integrações externas
As integrações externas (banco de dados, APIs ou outros serviços) devem ser consumidas por meio de interfaces definidas em `application/ports/` e implementadas em `infrastructure/`.
