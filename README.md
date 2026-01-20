# 🪕 Dandelion - Bot de RPG para Discord

O **Dandelion** é um bot de Discord focado no gerenciamento de campanhas de RPG de mesa, com temática baseada no universo de *The Witcher*. Ele oferece sistemas de fichas de personagem, bestiário automatizado (via web scraping), rolagem de dados, inventário, combate por turnos e um narrador auxiliado por Inteligência Artificial (Google Gemini).

## 🚀 Funcionalidades

* **📜 Sistema de Personagens:** Criação, armazenamento e visualização de fichas de personagens com atributos, história e imagens.
* **⚔️ Sistema de Combate:** Gerenciamento de batalha com iniciativa, turnos travados, barras de vida e log de combate.
* **🧠 Narrador IA (Dandelion):** Integração com Google Gemini para narrar cenas e resultados de ações complexas.
* **📚 Bestiário Automático:** Importação de monstros diretamente da Wiki do The Witcher, incluindo fraquezas e lore traduzida.
* **🎲 Rolagem de Dados:** Suporte a fórmulas de dados (ex: `1d20+5`, `2d6`).
* **🎒 Inventário & Habilidades:** Gerenciamento de itens e skills equipáveis.

---

## 🛠️ Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:

1. **Python 3.8** ou superior.
2. **Git** (opcional, para clonar o repositório).

Você também precisará de:

* Um **Token de Bot do Discord** (obtido no [Discord Developer Portal](https://www.google.com/search?q=https://discord.com/developers/applications)).
* Uma **Chave de API do Google Gemini** (obtida no [Google AI Studio](https://aistudio.google.com/)).

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

# Sua chave da API do Google Gemini (Privado)
GEMINI_API_KEY=sua_chave_api_gemini_aqui

```

> **Nota:** Nunca compartilhe este arquivo com ninguém.

---

## 📚 Dados do Bestiário (Seeds)

Os arquivos SQL usados para popular o bestiário ficam em `data/seeds/`. Ao iniciar o bot, o `database.py` aplica esses seeds automaticamente caso existam. Isso facilita organizar conteúdo e manter o banco atualizado com novas fontes.

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
* **(Mestre)** `/mestre_criar`: Cria uma ficha sem dono (NPC ou Player futuro).
* **(Mestre)** `/mestre_vincular`: Força a vinculação de uma ficha a um jogador.

### ⚔️ Combate

* `/combate_criar [monstro]`: Cria uma sala de combate contra um monstro do bestiário.
* `/combate_entrar`: Jogadores entram na batalha atual.
* `/combate_iniciar`: Rola iniciativa e trava o turno para o início.
* **(Botão)** `Atacar/Defender/Skill`: Ações dentro da interface de combate.
* **(Mestre)** `Destravar/Próximo`: Avança o turno (apenas o Mestre vê esse botão quando o jogo pausa).

### 📚 Bestiário & IA

* `/ver [nome]`: Exibe a ficha técnica e lore de uma criatura.
* `/alimentar_bestiario`: **(Atenção)** Inicia o web scraping da Wiki para popular o banco de dados (pode demorar).
* `/monstro_editar`: Ajusta HP e Iniciativa de um monstro importado.
* `/dandelion [solicitacao]`: Pede ao Mestre IA para narrar uma cena ou resultado.

### 🎲 Utilitários

* `/rolar [formula]`: Rola dados (ex: `1d20+3`).
* `/inventario`: Abre seu inventário para visualização ou venda de itens.
* `/usar_habilidade [slot]`: Usa uma habilidade equipada em um slot específico.

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
│   ├── bestiary.py       # Scraper e Bestiário
│   ├── characters.py     # Sistema de Fichas
│   ├── combat.py         # Lógica de Combate
│   ├── dice.py           # Dados
│   ├── inventory.py      # Inventário
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
