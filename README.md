# GUI-Agent

Planner (un LLM che Interpreta l'obiettivo, individua i vincoli e crea un piano di lavoro. Non stabilisce necessariamente tutti i click: può adattare il piano durante l'esecuzione) -> Agent/Controller (Osserva lo schermo, valuta lo stato attuale e sceglie autonomamente la prossima azione.) -> Action Executor (Python, Esegue click, doppio click, digitazione, scorciatoie e altre azioni consentite attraverso PyAutoGUI)  -> Verifier (Controlla che l'azione abbia avuto l'effetto previsto e che l'obiettivo finale sia stato raggiunto).


Non faremo lavorare tre LLM a ogni passaggio. Sarebbe costoso e spesso inutile. Il modello principale prende le decisioni; gli altri intervengono solo quando c'è un motivo preciso.

## Regole di progettazione per non sprecare API

Non chiamare l'AI per verifiche che Python può fare. Se dobbiamo sapere se un file esiste, usiamo il filesystem, non uno screenshot.



Non inviare screenshot inutilmente. Catturiamo lo schermo quando serve prendere una decisione o verificare un cambiamento.



Non ripetere la stessa richiesta. In caso di errore, registriamo il motivo e cambiamo strategia.



Limitare il contesto. Il modello riceve l'obiettivo, lo stato corrente, le ultime azioni e lo screenshot necessario, non tutta la cronologia dall'inizio.



Usare output strutturati. Il modello deve restituire azioni in un formato JSON validabile, non spiegazioni libere da interpretare.



Imporre limiti di sicurezza. Numero massimo di azioni, timeout, conferma per operazioni distruttive e possibilità di interrompere l'agente.



Registrare i costi. Ogni richiesta deve avere modello, token, tempo, esito e costo, quando il provider comunica questi dati.

> Una cosa importante: il modello non deve poter eseguire codice Python arbitrario. Deve scegliere tra strumenti autorizzati, ad esempio click, double_click, type_text, press_key, screenshot e wait.


## Struttura

```
gui_agent/
│
├── main.py
├── config.py
├── llm_client.py
│
├── agent/
│   ├── planner.py
│   ├── controller.py
│   ├── executor.py
│   ├── verifier.py
│   └── state.py
│
├── tools/
│   ├── screen.py
│   └── computer.py
│
├── logs/
│
└── .env
```

---

# Passo 1

Configutazione del progetto

```
sudo apt update
sudo apt install python3-full python3-venv

python3 -m venv .venv

source .venv/bin/activate

python -m pip install openai python-dotenv pydantic pyautogui pillow
```

Il progetto per ora operazioni semplici le fa, prossimo passo aggiungere il backtrack per risolvere qualche errorino (tipo nome sbagliao perché stava già un nome scritto e scrive affianco).
