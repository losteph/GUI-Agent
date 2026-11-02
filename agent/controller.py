
import json

from dataclasses import asdict, is_dataclass

from config import VISION_MODEL
from llm_client import ask_llm
from agent.actions import validate_controller_action


CONTROLLER_PROMPT = """
Sei il Controller di un GUI Agent che controlla un desktop Linux.

Devi raggiungere l'obiettivo osservando lo screenshot e scegliendo
UNA SOLA prossima azione concreta sulla GUI.

Il Planner ha già definito gli obiettivi di alto livello.
Tu devi tradurli in operazioni GUI atomiche.

REGOLE:

1. Osserva attentamente lo screenshot.
2. Considera il piano e le azioni già effettuate.
3. Scegli una sola azione atomica.
4. Non inventare elementi GUI che non sono visibili.
5. Non inventare coordinate.
6. Per click, double_click e right_click identifica il bersaglio
   visibile e fornisci un bounding box normalizzato.
7. Se non riesci a individuare un elemento, usa wait o verify.
8. Non generare codice, comandi shell o istruzioni arbitrarie.
9. Non eseguire azioni distruttive o potenzialmente pericolose.
10. Se manca un'informazione indispensabile, chiedi chiarimento.
11. Non ripetere azioni già completate.
12. Non scegliere azioni di alto livello del Planner.
13. Non dichiarare autonomamente il task completato.
14. Se ritieni che l'obiettivo sia stato raggiunto, scegli verify.

AZIONI CONSENTITE:

click
double_click
right_click
press_key
hotkey
type_text
scroll
wait
verify

PARAMETRI:

click, double_click, right_click:
{"bbox": [x_min, y_min, x_max, y_max]}

press_key:
{"key": "enter"}

hotkey:
{"keys": ["ctrl", "s"]}

type_text:
{"text": "testo da digitare"}

scroll:
{"amount": -3}

wait:
{"seconds": 1}

verify:
{"reason": "Motivo per richiedere una verifica"}

Il bounding box deve avere valori normalizzati tra 0 e 1
rispetto allo screenshot ricevuto.

FORMATO DI RISPOSTA:

Restituisci esclusivamente JSON valido:

{
  "action": "click",
  "parameters": {
    "bbox": [0.1, 0.2, 0.3, 0.4]
  },
  "short_reason": "Motivo sintetico",
  "expected_result": "Risultato atteso",
  "requires_verification": true,
  "task_completed": false,
  "needs_clarification": false,
  "clarification_question": null
}

task_completed deve rimanere false.
Solo il Verifier può confermare il completamento.

Non inserire spiegazioni fuori dal JSON.
"""


def extract_json(content):
    if not isinstance(content, str) or not content.strip():
        raise ValueError("La risposta del Controller è vuota")

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
            f"Il Controller non ha restituito JSON valido: {exc}"
        ) from exc


def build_controller_context(
    instruction,
    plan,
    task_state,
    recent_actions
):
    if is_dataclass(task_state):
        task_state = asdict(task_state)

    if not isinstance(recent_actions, list):
        raise ValueError("recent_actions deve essere una lista")

    return {
        "instruction": instruction,
        "plan": plan,
        "task_state": task_state,
        "recent_actions": recent_actions[-5:]
    }


def validate_decision(decision):
    if not isinstance(decision, dict):
        raise ValueError("La decisione non è un oggetto JSON valido")

    required = {
        "action",
        "parameters",
        "short_reason",
        "expected_result",
        "requires_verification",
        "task_completed",
        "needs_clarification",
        "clarification_question"
    }

    if not required.issubset(decision):
        raise ValueError("Campi mancanti nella decisione")

    action = decision["action"]

    if not isinstance(action, str) or not validate_controller_action(action):
        raise ValueError(f"Azione Controller non consentita: {action}")

    parameters = decision["parameters"]

    if not isinstance(parameters, dict):
        raise ValueError("Parameters deve essere un oggetto")

    for field in ("short_reason", "expected_result"):
        if not isinstance(decision[field], str):
            raise ValueError(f"{field} deve essere una stringa")

    for field in (
        "task_completed",
        "requires_verification",
        "needs_clarification"
    ):
        if not isinstance(decision[field], bool):
            raise ValueError(f"{field} deve essere booleano")

    question = decision["clarification_question"]

    if question is not None and not isinstance(question, str):
        raise ValueError("clarification_question non valida")

    if decision["needs_clarification"] and not question:
        raise ValueError("Manca la domanda di chiarimento")

    if decision["task_completed"]:
        raise ValueError(
            "Il Controller non può confermare il completamento"
        )

    if action in {"click", "double_click", "right_click"}:
        bbox = parameters.get("bbox")

        if not isinstance(bbox, list) or len(bbox) != 4:
            raise ValueError("Bounding box mancante o non valido")

        if not all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and 0 <= value <= 1
            for value in bbox
        ):
            raise ValueError("Coordinate fuori dall'intervallo 0-1")

        x1, y1, x2, y2 = bbox

        if x1 >= x2 or y1 >= y2:
            raise ValueError("Bounding box con dimensioni non valide")

    if action == "hotkey":
        keys = parameters.get("keys")

        if not isinstance(keys, list) or not 1 <= len(keys) <= 3:
            raise ValueError("Hotkey non valida")

        if not all(isinstance(key, str) for key in keys):
            raise ValueError("I tasti devono essere stringhe")

    if action == "type_text":
        if not isinstance(parameters.get("text"), str):
            raise ValueError("Testo da digitare non valido")

    if action == "press_key":
        if not isinstance(parameters.get("key"), str):
            raise ValueError("Tasto non valido")

    if action == "scroll":
        amount = parameters.get("amount")

        if (
            not isinstance(amount, int)
            or isinstance(amount, bool)
            or not -10 <= amount <= 10
        ):
            raise ValueError("Valore di scroll non valido")

    if action == "wait":
        seconds = parameters.get("seconds", 1)

        if (
            not isinstance(seconds, (int, float))
            or isinstance(seconds, bool)
            or not 0 <= seconds <= 10
        ):
            raise ValueError("Durata di attesa non valida")

    return decision


def decide_next_action(
    instruction,
    plan,
    task_state,
    recent_actions,
    screenshot
):
    if not isinstance(screenshot, dict):
        raise ValueError("Screenshot non valido")

    image_base64 = screenshot.get("image_base64")

    if not isinstance(image_base64, str) or not image_base64:
        raise ValueError("Immagine dello screenshot mancante")

    context = build_controller_context(
        instruction,
        plan,
        task_state,
        recent_actions
    )

    messages = [
        {
            "role": "system",
            "content": CONTROLLER_PROMPT
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Stato del task:\n"
                        + json.dumps(context, ensure_ascii=False)
                        + "\n\nAnalizza lo screenshot e scegli "
                        "una sola prossima azione."
                    )
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            "data:image/jpeg;base64,"
                            + image_base64
                        )
                    }
                }
            ]
        }
    ]

    response = ask_llm(
        model=VISION_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=700
    )

    decision = extract_json(response["content"])

    validate_decision(decision)

    return decision
