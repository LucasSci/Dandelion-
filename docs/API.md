# API (REST + GraphQL)

A API do Dandelion expõe endpoints REST e GraphQL com autenticação por API key, versionamento `/v1` e rate limiting.

## Autenticação

Use o header `X-API-Key` ou `Authorization: Bearer <API_KEY>`.

Variáveis de ambiente:

- `DANDELION_API_KEY` (padrão: `dev-secret`)
- `DANDELION_RATE_LIMIT` (padrão: `60` requisições)
- `DANDELION_RATE_LIMIT_WINDOW` (padrão: `60` segundos)

## Versionamento

Todos os endpoints REST vivem sob `/v1`. O GraphQL é `/v1/graphql`.

## Rate limiting

Por padrão, 60 requisições por 60 segundos por API key + rota.

## OpenAPI

A documentação automática (OpenAPI) é servida pelo FastAPI:

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

## REST (exemplos)

```bash
curl -X POST http://localhost:8000/v1/roll_skill \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"stat": 6, "skill": 4}'
```

```bash
curl -X POST http://localhost:8000/v1/generate_map \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"width": 20, "height": 20, "biome": "forest"}'
```

## GraphQL (exemplo)

```bash
curl -X POST http://localhost:8000/v1/graphql \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"query": "mutation($payload: RollSkillInput!) { rollSkill(payload: $payload) { total rolls } }", "variables": {"payload": {"stat": 6, "skill": 4}}}'
```

## SDKs

SDKs simples em `sdk/js` e `sdk/python` com autenticação padrão por `X-API-Key`.

### JavaScript

```js
import { DandelionClient } from "./sdk/js/client.js";

const client = new DandelionClient({
  baseUrl: "http://localhost:8000",
  apiKey: "dev-secret",
});

const result = await client.rollSkill({ stat: 6, skill: 4 });
console.log(result);
```

### Python

```python
from sdk.python.client import DandelionClient

client = DandelionClient(
    base_url="http://localhost:8000",
    api_key="dev-secret",
)

result = client.roll_skill(stat=6, skill=4)
print(result)
```
