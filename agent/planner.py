
import json

from config import PLANNER_MODEL
from llm_client import ask_llm
from agent.actions import PLANNER_ACTIONS, validate_planner_action
from agent.state import TaskState, TaskStep


PLANNER_SYSTEM_PROMPT = """
Sei il Planner di un GUI Agent.

Il tuo compito è trasformare istruzioni in linguaggio naturale
in un piano operativo per controllare un computer Linux.

Non devi eseguire azioni.
Devi soltanto pianificare.

Regole:

1. Comprendi l'obiettivo finale dell'utente.
2. Suddividi il lavoro in passaggi chiari e ordinati.
3. Non inventare informazioni mancanti.
4. Preferisci operazioni semplici e verificabili.
5. Non inserire coordinate del mouse.
6. Non generare codice Python o comandi shell.
7. Usa esclusivamente le azioni di alto livello consentite.
8. Non inserire clic, pressioni di tasti o altre operazioni GUI.
9. Non aggiungere passaggi superflui.
10. Se manca un'informazione indispensabile, chiedi chiarimenti.

Azioni consentite:
open_application, create_folder, open_folder,
create_file, write_text, save_file, close_window.

Restituisci esclusivamente JSON valido, senza Markdown.

Formato:

{
  "goal": "descrizione dell'obiettivo",
  "needs_clarification": false,
  "clarification_question": null,
  "steps": [
    {
      "action": "create_folder",
      "description": "Crea una cartella",
      "parameters": {
        "location": "desktop",
        "name": "PROVA"
      }
    }
  ],
  "success_criteria": [
    "La cartella esiste sul desktop"
  ]
}

Se servono chiarimenti:
- imposta needs_clarification a true;
- inserisci la domanda in clarification_question;
- non inventare i dati mancanti.
"""


def extract_json(content: str) -> dict:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("La risposta del Planner è vuota")

    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()

        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]

        content = "\n".join(lines).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Il Planner non ha restituito JSON valido: {exc}"
        ) from exc


def create_plan(instruction: str) -> dict:
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError("L'istruzione dell'utente è vuota")

    messages = [
        {
            "role": "system",
            "content": PLANNER_SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": instruction
        }
    ]

    response = ask_llm(
        model=PLANNER_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=1200
    )

    plan = extract_json(response["content"])
    validate_plan(plan)

    return plan


def validate_plan(plan: dict):
    required_fields = {
        "goal",
        "needs_clarification",
        "clarification_question",
        "steps",
        "success_criteria"
    }

    if not isinstance(plan, dict):
        raise ValueError("Il piano deve essere un oggetto JSON")

    if not required_fields.issubset(plan.keys()):
        raise ValueError("Campi obbligatori mancanti")

    if not isinstance(plan["goal"], str) or not plan["goal"].strip():
        raise ValueError("Goal non valido")

    if not isinstance(plan["needs_clarification"], bool):
        raise ValueError("needs_clarification deve essere booleano")

    question = plan["clarification_question"]

    if question is not None and not isinstance(question, str):
        raise ValueError("clarification_question non valida")

    if plan["needs_clarification"] and not question:
        raise ValueError("Manca la domanda di chiarimento")

    if not isinstance(plan["steps"], list):
        raise ValueError("Steps deve essere una lista")

    if len(plan["steps"]) > 30:
        raise ValueError("Il piano contiene troppi passaggi")

    for index, step in enumerate(plan["steps"]):
        if not isinstance(step, dict):
            raise ValueError(f"Step {index} non valido")

        action = step.get("action")

        if not isinstance(action, str) or not validate_planner_action(action):
            raise ValueError(f"Azione Planner non consentita: {action}")

        if not isinstance(step.get("description"), str):
            raise ValueError(f"Description dello step {index} non valida")

        if not isinstance(step.get("parameters", {}), dict):
            raise ValueError(f"Parameters dello step {index} non validi")

    if not isinstance(plan["success_criteria"], list):
        raise ValueError("Success criteria deve essere una lista")

    if not all(
        isinstance(item, str) and item.strip()
        for item in plan["success_criteria"]
    ):
        raise ValueError("I criteri di successo devono essere stringhe non vuote")

    if not plan["needs_clarification"] and not plan["steps"]:
        raise ValueError("Il piano non contiene passaggi operativi")


def build_task_state(instruction: str, plan: dict) -> TaskState:
    validate_plan(plan)

    if plan["needs_clarification"]:
        raise ValueError(
            "Non è possibile creare lo stato del task: "
            "sono necessari chiarimenti"
        )

    steps = [
        TaskStep(
            id=index + 1,
            action=step["action"],
            description=step["description"],
            parameters=step.get("parameters", {})
        )
        for index, step in enumerate(plan["steps"])
    ]

    return TaskState(
        task_id="task_001",
        original_instruction=instruction,
        goal=plan["goal"],
        steps=steps
    )
