# 🪕 Dandelion - Bot de RPG para Discord

O **Dandelion** é um bot de Discord focado no gerenciamento de campanhas de RPG de mesa, com temática baseada no universo de *The Witcher*. Ele oferece sistemas de fichas de personagem, bestiário automatizado (seeds/importações), rolagem de dados, inventário, combate por turnos e um narrador auxiliado por Inteligência Artificial (OpenAI/Gemini).

## 🚀 Funcionalidades

* **📜 Sistema de Personagens:** Criação de fichas, pool de personagens, exportação JSON, atributos, armaduras por localização, XP/nível, ouro e localização atual.
* **⚔️ Sistema de Combate:** Criação de sala, entrada de jogadores, iniciativa, avanço de turnos, aplicação de dano e exportação do log em Markdown.
* **🧠 Narrador IA (Dandelion):** Integração com OpenAI para narrar cenas, gerar missões cronológicas, diálogos de NPC e itens.
* **📚 Bestiário Automático:** Seeds de criaturas, consulta com teste de Monster Lore, edição de monstros e geração de arte estilo Witcher.
* **🗺️ Lore & Memória de Campanha:** Diário de campanha, banco de lore com importação de `.txt` e eventos com consequências.
* **🎲 Rolagem de Dados:** Suporte a fórmulas de dados (ex: `1d20+5`, `2d6`).
* **🎒 Inventário & Habilidades:** Visualização de inventário e uso de habilidades rápidas.
* **📜 Quests & Contratos:** Criação manual/IA, publicação em fórum, atribuição a jogadores e conclusão com recompensas.
* **🧑‍🤝‍🧑 NPCs e Rumores:** Cadastro de NPCs com personalidade, interação por IA e sorteio de rumores.
* **🏪 Economia & Loja:** Loja com estoque, geração de itens por IA e controle de preços.
* **🏅 Progressão Social:** Facções, reputação, conquistas, legados e comparação de builds.
* **🧭 Campanha Solo:** Progresso individual, diário e recursos coletados.
* **🛠️ Utilitários:** Status do bot e minijogo de Gwent.

---

## 🧠 Integração (O “Cérebro” do Sistema)

**Fluxo de dados macro:**

1. O mestre digita no Discord: `/combate_iniciar` → o bot gera um link para o VTT.
2. No VTT, o jogador move o token.
3. O VTT envia via WebSocket a nova posição.
4. O jogador clica em **Atacar** na ficha web.
5. O sistema calcula o acerto vs. Defesa do alvo.
6. O bot no Discord anuncia: **“Geralt acertou o Ghoul por 15 de dano (Prata)!”** e atualiza o HP do monstro no VTT.

---

## 🧭 Roadmap de Ideias (Em Estudo)

> Estes itens representam o **futuro desejado** do projeto. O progresso pode ser acompanhado pelo comando `/roadmap`.

### 🎭 Narrativa IA e Experiência de Jogo

* Memória de campanha entre sessões para contexto prolongado.
* NPCs com personalidade dinâmica (estilo, humor e hábitos próprios).
* Histórias procedurais com ramificações e consequências persistentes.
* Gerador de quests com objetivos e recompensas variáveis.
* Narrador adaptativo com ajuste automático de dificuldade.
* Gerador de lore & ambientação por bioma/clima.
* Análises narrativas pós-sessão (resumos automáticos).
* Sistema de rumores e ganchos de história automáticos.
* Diálogos de NPC com voz sintetizada opcional.

### ⚔️ Combate e Mecânicas

* Sistema de iniciativa avançado com alertas visuais e sons.
* Combate em grid com mapas e tokens interativos.
* Grid com alternância entre hexagonal (viagens) e quadrado (combate), com escala de 1 quadrado = 2m (regra oficial).
* Tokens vinculados à ficha do jogador, com barra de HP e Stamina flutuante sobre o token.
* Fog of War dinâmica: mestre vê tudo; jogadores veem apenas raio de visão e fontes de luz (tochas).
* Integração com mapas externos (Roll20/Foundry) via API.
* Ferramentas de efeitos de status e condições automatizadas.
* Voz de mestre de combate automatizada (descrições sonoras).
* Logs de combate exportáveis (PDF/Markdown).
* Sistema de eventos aleatórios em combate.
* Estatísticas detalhadas por jogador/monstro.
* Regras customizadas baseadas no sistema específico de RPG.
* Ferramentas de balanceamento de encontros e sugestões de ajustes.
* Hazards de terreno difícil (lama, fogo) que reduzem o movimento automaticamente.
* Line of Sight (LoS): paredes bloqueiam visão e movimento.

### 🗺️ Tabletop & Battlemaps (VTT Procedural)

* Grid tático web-based (Canvas/WebGL) para execução das cenas.
* Geração procedural de mapas via Wave Function Collapse ou Perlin Noise.
* Inputs do usuário para bioma (pântano, floresta, caverna, cidade), tamanho (ex: 20x20) e clima (chuva, sol).
* Seleção automática de tilesets conforme o bioma (ex: tiles de lama para pântano).

### 📇 Personagens e Progressão

* Sistema de níveis, talentos e subclasses expansível.
* Interface visual de criação de personagem.
* Histórico de progresso e conquistas.
* Ferramenta de ponderação de atributos baseado em papéis.
* Sincronização com fichas de PDF ou fichas externas.
* Comparador de builds (stats/skills).
* Mecânica de reputação e facções.
* Árvore de habilidades visual e customizável.
* Importação/exportação de fichas em formatos populares.
* Sistema de legado (benefícios de campanhas anteriores).

### 🗂️ Organização da Campanha (The GM Grimoire)

* Painel administrativo para o mestre organizar o mundo de forma relacional.
* NPCs com ficha simplificada, campo de disposição (Aliado/Neutro/Inimigo) e localização atual.
* Bestiário com importação do livro oficial e sistema de "Witcher Knowledge" (fraquezas visíveis apenas após teste de Monster Lore definido pelo mestre).
* Quest Log ramificado com árvore de decisões e estado atual salvo.

### 📦 Bestiário e Conteúdo Coletado

* Scraping inteligente de múltiplas fontes de lore.
* Banco de dados colaborativo com votação de usuários.
* Imagens geradas por IA (criaturas, mapas, itens).
* Tabelas aleatórias de encontros por região/nível.
* Bestiário multilíngue com traduções automáticas.
* Tags de ambiente e biome para criaturas e eventos.
* Comparador de monstros por atributos e fraquezas.
* Sistema de contramedidas automáticas (resistências/fraquezas).
* Edição colaborativa de bestiário via comandos de chat.
* Bestiário temático (fantasia sombria, steampunk, sci-fi, etc.).

### 🪄 Utilitários e Qualidade de Vida

* Dashboard web para administradores de campanha.
* Sistema de backups e snapshots automáticos.
* Logs avançados com busca e filtros.
* Modularização de comandos (ativar/desativar módulos).
* Sistema de permissões granular para mestres/equipe.
* Temas de UI customizáveis (cores, emojis, layouts).
* Lembretes e eventos programados (sessões, quests).
* Sistema de economia e crafting com simulação de mercado.
* Tabelas de loot procedurais baseadas na região (ex: Velen = loot pobre/crafting; Toussaint = vinho/ouro/armas finas).
* Integração com plataformas externas (Twitch, Patreon).
* Suporte nativo a múltiplas línguas com localização automática.

### 🌟 Bônus de Potência

* Plugins oficiais para diferentes sistemas de RPG (D&D, Pathfinder, World of Darkness, L5R, etc.).
* Comando de “minuto de mestre” com resumo e sugestões em tempo real.
* Modo solo com IA mestre para aventuras single-player.

---

## 🛠️ Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:

1. **Python 3.8** ou superior.
2. **Git** (opcional, para clonar o repositório).

Você também precisará de:

* Um **Token de Bot do Discord** (obtido no [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications)).
* Uma **Chave de API da OpenAI** (para narrador, NPCs, quests e arte).
* (Opcional) **Chave de API do Google Gemini** (para comandos de teste/visão).

---

## 📦 Instalação Passo a Passo

### 1. Clone o repositório

Baixe os arquivos para uma pasta em seu computador.

```bash
git clone https://github.com/seu-usuario/dandelion-bot.git
cd dandelion-bot

```

### 2. Crie um Ambiente Virtual (Recomendado)

Para evitar conflitos de bibliotecas, crie um ambiente virtual:

**Windows:**

```bash
python -m venv venv
.\venv\Scripts\activate

```

**Linux/Mac:**

```bash
python3 -m venv venv
source venv/bin/activate

```

### 3. Instale as Dependências

Instale todas as bibliotecas necessárias listadas no `requirements.txt`:

```bash
pip install -r requirements.txt

```

---

## ⚙️ Configuração

Crie um arquivo chamado `.env` na raiz do projeto (mesma pasta do `bot.py`). Abra-o com um editor de texto e insira as suas chaves conforme o modelo abaixo:

```ini
# Arquivo .env

# Seu token do Discord (Privado)
DISCORD_TOKEN=seu_token_do_discord_aqui

# Sua chave da API da OpenAI (Privado)
OPENAI_API_KEY=sua_chave_api_openai_aqui

# Sua chave da API do Google Gemini (Privado)
GEMINI_API_KEY=sua_chave_api_gemini_aqui

# (Opcional) Link da campanha no Roll20 para abrir pelo botão do tabletop
ROLL20_CAMPAIGN_URL=https://app.roll20.net/campaigns/details/123456789/campanha

```

> **Nota:** Nunca compartilhe este arquivo com ninguém.

---

## 📚 Dados do Bestiário (Seeds)

Os arquivos SQL usados para popular o bestiário ficam em `data/seeds/`. Ao iniciar o bot, o `database.py` aplica esses seeds automaticamente caso existam. Isso facilita organizar conteúdo e manter o banco atualizado com novas fontes.

---

## 🧾 Schema JSON da Ficha (Witcher)

Para suportar a ficha digital baseada em JSON, o schema canônico está em `data/schemas/character_sheet.schema.json` e um exemplo em `data/schemas/character_sheet.example.json`. Esse arquivo define `Core Stats`, `Derived Stats`, `Skills Tree`, `Witcher Specifics` e `Armor Layers`, servindo como base para validação automática de regras.

---

## ▶️ Como Rodar

Com o ambiente virtual ativado e as dependências instaladas, inicie o bot:

```bash
python bot.py

```

Se tudo der certo, você verá no terminal:

```
⚔️ Sistema de Combate carregado.
✅ Bot pronto e comandos sincronizados.
🚀 Dandelion online como NomeDoSeuBot#1234

```

---

## 🎮 Comandos Disponíveis

O bot utiliza **Slash Commands** (`/`). Digite `/` no Discord para ver o menu interativo.

### 📜 Personagens & Fichas

* `/criar_ficha`: Abre um formulário para criar seu personagem.
* `/ficha [usuario]`: Exibe o painel interativo do personagem (Skills, Lore, Stats).
* `/listar_fichas`: Lista todos os personagens no banco de dados.
* `/devolver_ficha`: Devolve seu personagem para o "Pool" (útil para trocar de char).
* `/assumir_personagem`: Pega um personagem livre do "Pool".
* `/ficha_exportar`: Exporta a ficha em JSON.
* `/localizacao`: Mostra a localização atual do personagem.
* `/viajar`: Define a localização atual do personagem.
* `/atributo_definir`: Define o valor de um atributo.
* `/atributo_listar`: Lista atributos cadastrados.
* `/armadura_definir`: Define o SP da armadura por localização.
* `/armadura_modificador`: Define modificadores de dano por localização.
* `/receber_dano`: Aplica dano com SP e modificadores de armadura.
* **(Mestre)** `/mestre_criar`: Cria uma ficha sem dono (NPC ou Player futuro).
* **(Mestre)** `/mestre_vincular`: Força a vinculação de uma ficha a um jogador.
* **(Mestre)** `/mestre_add_xp`: Dá XP ao jogador e processa Level Up.
* **(Mestre)** `/mestre_levelup`: Força a subida de 1 nível.
* **(Mestre)** `/mestre_leveldown`: Remove 1 nível (corrige erro).
* **(Mestre)** `/mestre_ouro`: Adiciona ou remove ouro.

### ⚔️ Combate

* `/combate_criar [monstro]`: Cria uma sala de combate contra um monstro do bestiário.
* `/combate_adicionar`: Adiciona criaturas ao combate.
* `/combate_entrar`: Jogadores entram na batalha atual.
* `/combate_iniciar`: Rola iniciativa e trava o turno para o início.
* `/combate_exportar`: Exporta o log de combate em Markdown.
* **(Botão)** `Atacar/Defender/Skill`: Ações dentro da interface de combate.
* **(Mestre)** `Destravar/Próximo`: Avança o turno (apenas o Mestre vê esse botão quando o jogo pausa).

### 📚 Bestiário & IA

* `/ver [nome]`: Exibe a ficha técnica e lore de uma criatura (com teste de Monster Lore).
* `/alimentar_bestiario`: Reaplica seeds e atualiza tabelas base do bestiário.
* `/monstro_editar`: Ajusta HP, iniciativa, dano e CD de Monster Lore.
* `/gerar_imagem`: Gera arte estilo *Witcher 3 Journal*.
* `/dandelion [solicitacao]`: Pede ao Mestre IA para narrar uma cena ou resultado.
* `/teste_gerar_prompt`: [DEV] Gera prompt de imagem baseado em uma URL (Gemini).

### 🎲 Utilitários

* `/rolar [formula]`: Rola dados (ex: `1d20+3`).
* `/inventario`: Abre seu inventário para visualização.
* `/usar_habilidade [slot]`: Usa uma habilidade equipada em um slot específico.
* `/status`: Mostra status do bot e integrações.

### 🗺️ Campanha, Lore & Memória

* `/diario ver`: Exibe a linha do tempo atual.
* `/diario adicionar`: Registra um evento no diário.
* `/diario consequencia`: Registra consequência persistente.
* `/diario importar_txt`: Importa um resumo longo via `.txt`.
* `/diario editar`: Corrige um evento salvo.
* `/diario apagar`: Remove um evento.
* `/diario limpar_tudo`: Reseta toda a memória.
* `/lore ver`: Lista fatos de mundo salvos.
* `/lore adicionar`: Registra um novo fato para a IA.
* `/lore importar_txt`: Importa lore via `.txt`.
* `/lore editar`: Corrige um lore.
* `/lore apagar`: Remove um lore.
* `/lore limpar_tudo`: Apaga todo o banco de lore.
* `/mundo definir_bioma`: Define bioma e clima de uma região.
* `/mundo ambientacao`: Gera ambientação por bioma/clima.
* `/memoria_importar`: Upload de `.txt` para memória de campanha.

### 📜 Quests & Contratos

* `/quest_criar`: Cria missão manualmente com fórum e recompensas.
* `/quest_gerar`: IA cria missão cronológica (rascunho ou publicação).
* `/quest_gerar_auto`: IA escolhe dificuldade pela média do grupo.
* `/quest_publicar`: Publica um rascunho no fórum.
* `/quest_atribuir`: Força a entrada de um jogador.
* `/quest_concluir`: Finaliza missão e distribui recompensas.

### 🧑‍🤝‍🧑 NPCs, Rumores & Sessões

* `/npc_criar`: Cria NPC com personalidade dinâmica.
* `/npc_ver`: Exibe ficha do NPC.
* `/npc_falar`: Interage com NPC via IA.
* `/rumor_adicionar`: Adiciona rumor/gancho.
* `/rumor_listar`: Lista rumores.
* `/rumor_sortear`: Sorteia um rumor ativo.
* `/rumor_usar`: Marca rumor como usado.
* `/sessao_iniciar`: Inicia gravação do chat.
* `/sessao_pausar`: Pausa as anotações.
* `/call_entrar`: Dandelion entra na call e registra eventos.
* `/call_sair`: Dandelion sai da call e encerra registros.
* `/sessao_finalizar`: Gera o diário narrativo da sessão.

### 🏪 Economia, Progresso & Extras

* `/loja`: Abre a loja de itens.
* `/loja_adicionar`: Adiciona item à loja.
* `/loja_gerar`: Gera item via IA.
* `/loja_estoque`: Lista estoque da loja.
* `/loja_remover`: Remove item do estoque.
* `/faccao_criar`: Cria facção.
* `/faccao_listar`: Lista facções.
* `/reputacao_definir`: Define reputação com uma facção.
* `/reputacao_ver`: Exibe reputações.
* `/conquista_criar`: Registra conquista.
* `/conquista_dar`: Concede conquista.
* `/conquistas_ver`: Lista conquistas de um jogador.
* `/legado_adicionar`: Registra legado de campanha.
* `/legado_ver`: Exibe legados.
* `/comparar_builds`: Compara atributos entre personagens.
* `/atributos_sugerir`: Sugere pesos de atributos por papel.
* `/gwent`: Batalha de cartas em rounds com clima, linhas e turnos automáticos.

### 🧭 Campanha Solo

* `/solo_iniciar`: Inicia campanha solo com progresso individual.
* `/solo_avancar`: Avança capítulos e ganha XP/recursos.
* `/solo_diario`: Exibe entradas recentes do diário solo.
* `/solo_recursos`: Lista recursos coletados.

---

## 📁 Estrutura do Projeto

```
/
├── bot.py                # Arquivo principal de inicialização
├── config.py             # Configurações centralizadas (tokens, extensões)
├── database.py           # Gerenciamento do SQLite (Cria tabelas)
├── utils.py              # Funções auxiliares (Rolagem de dados)
├── requirements.txt      # Lista de dependências
├── .env                  # Chaves de API (Você deve criar)
├── data/                 # Dados auxiliares do projeto
│   └── seeds/            # Seeds SQL para popular o bestiário
├── cogs/                 # Módulos de comandos
│   ├── ai_handler.py     # Integração Google Gemini
│   ├── bestiary.py       # Bestiário, seeds e arte
│   ├── campaign.py       # Linha do tempo e lore do mundo
│   ├── characters.py     # Sistema de Fichas
│   ├── combat.py         # Lógica de Combate
│   ├── dice.py           # Dados
│   ├── gwent.py          # Minijogo de Gwent
│   ├── inventory.py      # Inventário
│   ├── npcs.py           # NPCs com personalidade
│   ├── progress.py       # Facções, reputação e conquistas
│   ├── quests.py         # Quests e contratos
│   ├── roadmap.py        # Roadmap do projeto
│   ├── rumors.py         # Rumores e ganchos
│   ├── scribe.py         # Escriba da sessão
│   ├── shop.py           # Economia/loja
│   └── skills.py         # Habilidades rápidas
└── ui/                   # Interfaces Visuais (Botões/Modais)
    ├── combat_view.py    # Interface da batalha
    ├── modals.py         # Formulários de preenchimento
    └── sheet_view.py     # Painel da ficha

```

---

## ⚠️ Solução de Problemas Comuns

1. **Erro `Privileged Intents`:**
* Vá no Discord Developer Portal -> Bot -> Privileged Gateway Intents.
* Ative: **Presence Intent**, **Server Members Intent** e **Message Content Intent**.


2. **Comandos não aparecem:**
* Pode levar até 1 hora para o Discord registrar comandos globais pela primeira vez, embora o código force a sincronização (`sync`). Tente reiniciar o bot.


3. **Banco de Dados:**
* O arquivo `bestiario.db` é criado automaticamente na primeira execução. Se der erro de coluna faltando, apague o arquivo `.db` e reinicie o bot (cuidado, isso apaga os dados salvos).
