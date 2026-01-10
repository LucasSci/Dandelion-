import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Carrega a chave do .env
load_dotenv()
CHAVE = os.getenv("GEMINI_API_KEY")

def chat_terminal():
    if not CHAVE:
        print("❌ Chave não encontrada no .env!")
        return

    client = genai.Client(api_key=CHAVE)
    
    # Usando o 1.5-flash que é mais resiliente no plano free
    MODELO = "gemini-2.5-flash" 

    print(f"--- Chat Zerrikania (Modelo: {MODELO}) ---")
    print("Digite sua mensagem (ou 'sair'):\n")

    while True:
        pergunta = input("➤ Você: ")
        if pergunta.lower() in ['sair', 'exit']: break

        try:
            response = client.models.generate_content(
                model=MODELO,
                contents=pergunta,
                config=types.GenerateContentConfig(
                    system_instruction="Seja breve e direto.",
                    temperature=0.7
                )
            )
            print(f"🪕 Dandelion: {response.text}\n")

        except Exception as e:
            if "429" in str(e):
                print("\n⚠️ LIMITE ATINGIDO (Plano Free).")
                print("O Google pede para você esperar uns 60 segundos antes da próxima pergunta.\n")
                # Opcional: time.sleep(60) para travar o script se quiser ser rigoroso
            else:
                print(f"\n❌ Erro: {e}\n")

if __name__ == "__main__":
    chat_terminal()