export class DandelionClient {
  constructor({ baseUrl = "http://localhost:8000", apiKey = "dev-secret" } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.apiKey = apiKey;
  }

  async request(path, payload) {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": this.apiKey,
      },
      body: JSON.stringify(payload ?? {}),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Request failed (${response.status}): ${text}`);
    }

    return response.json();
  }

  rollSkill(payload) {
    return this.request("/v1/roll_skill", payload);
  }

  combatUpdate(payload) {
    return this.request("/v1/combat_update", payload);
  }

  generateMap(payload) {
    return this.request("/v1/generate_map", payload);
  }

  vttEvent(payload) {
    return this.request("/v1/vtt/event", payload);
  }

  graphql(query, variables = {}) {
    return this.request("/v1/graphql", { query, variables });
  }
}
