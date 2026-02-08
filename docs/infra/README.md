# Infraestrutura como Código (IaC)

Este diretório descreve como versionar e evoluir a infraestrutura do Dandelion usando IaC.
O objetivo é permitir ambientes consistentes (dev/staging/prod) e facilitar rollback e deploy canário.

## Estrutura sugerida

```
infra/
├── envs/
│   ├── dev/
│   ├── staging/
│   └── prod/
├── modules/
│   ├── app/
│   ├── database/
│   └── observability/
└── README.md
```

- **envs/**: contém a configuração específica por ambiente (variáveis e parâmetros).
- **modules/**: módulos reutilizáveis para recursos comuns (app, banco, observabilidade).

## Ferramenta recomendada

Use **Terraform** (ou outro IaC equivalente) para declarar:

- VPC/rede e sub-redes.
- Banco de dados gerenciado.
- Cluster/serviço de execução do bot e APIs.
- Observabilidade (logs, métricas, alertas).

## Convenções

- Cada ambiente tem seu próprio estado (backend remoto recomendado).
- Use *workspaces* apenas se fizer sentido no seu provedor; prefira `envs/` separados.
- Versão e valide o plano (`terraform plan`) antes de aplicar (`terraform apply`).

## Integração com CI/CD

Os workflows em `.github/workflows/deploy.yml` assumem que os manifests/planos IaC
são aplicados durante o deploy. Ajuste os comandos em `scripts/deploy.sh` para:

1. Aplicar mudanças IaC do ambiente alvo (ex.: `terraform apply`).
2. Fazer deploy canário da aplicação.
3. Promover ou executar rollback.

## Rollback e canário

- Mantenha versões versionadas de manifests e releases.
- O rollback deve restaurar o último release estável no ambiente correspondente.
- Configure métricas e healthchecks para garantir promoção segura do canário.
