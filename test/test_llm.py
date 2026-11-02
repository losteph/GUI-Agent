# TEST COLLEGAMENTO: Per adesso non scriviamo ancora il Planner, verifichiamo che il client funzioni.
# Dobbiamo ottenere CONNESSIONE OK e visualizzare il consumo di token.

from config import PLANNER_MODEL
from llm_client import ask_llm

messages = [
    {
        "role": "user",
        "content": "Rispondi esclusivamente con: CONNESSIONE OK"
    }
]

try:
    result = ask_llm(
        model=PLANNER_MODEL,
        messages=messages,
        max_tokens=30
    )

    print("Risposta:", result["content"])
    print("Modello:", result["model"])
    print("Token:", result["usage"])

except Exception as error:
    print("Errore API:", type(error).__name__, str(error))
