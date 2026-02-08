# Políticas de Segurança

## 1) Objetivo
Estas políticas definem os controles mínimos de **RBAC/ABAC**, **MFA**, **auditoria de ações** e **criptografia de dados sensíveis** para a API de integração do VTT.

## 2) RBAC (Role-Based Access Control)
- **Papéis suportados**: `admin`, `gm`, `player`, `auditor`.
- **Permissões padrão**:
  - `admin`: acesso total (`*`).
  - `gm`: `vtt:roll`, `vtt:combat:update`, `vtt:event:publish`, `vtt:map:generate`.
  - `player`: `vtt:roll`, `vtt:map:generate`.
  - `auditor`: `vtt:audit:read`.
- Os papéis são enviados por cabeçalho: `X-User-Roles` (lista separada por vírgula) ou `X-User-Role`.

## 3) ABAC (Attribute-Based Access Control)
A avaliação de atributos é aplicada **em conjunto** com RBAC. Regras mínimas:
- **Organização**: se `X-Resource-Org` estiver presente, deve ser igual a `X-User-Org`.
- **Proprietário**: se `X-Resource-Owner` estiver presente, o acesso só é permitido ao proprietário ou a `gm`/`admin`.
- **Classificação**: se `X-Resource-Classification=restricted`, apenas `gm`/`admin` têm acesso.

## 4) MFA (Multi-Factor Authentication)
- Endpoints sensíveis exigem MFA (`vtt:event:publish`).
- O token TOTP é enviado pelo cabeçalho `X-MFA-Token`.
- Segredos MFA são obtidos por:
  - `MFA_SECRET_<USER_ID>` (prioritário), ou
  - `MFA_SHARED_SECRET`.

## 5) Auditoria de ações
- Todas as decisões de autorização são auditadas em `data/audit.log` (JSON Lines).
- O caminho pode ser sobrescrito por `AUDIT_LOG_PATH`.
- Campos sensíveis (ex.: `user_id`) são criptografados antes do registro.

## 6) Criptografia de dados sensíveis
- Chave de criptografia definida em `DATA_ENCRYPTION_KEY` (formato Fernet).
- Dados sensíveis devem ser protegidos usando `encrypt_sensitive_data` antes de persistência.

## 7) Boas práticas operacionais
- Rotação periódica de chaves `DATA_ENCRYPTION_KEY` e segredos MFA.
- Revisão de permissões e papéis a cada nova release.
- Monitoramento de alertas para eventos de negação (`allowed=false`).
