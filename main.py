import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from config import validate_config, VISION_MODEL
from llm_client import ask_llm

from agent.planner import create_plan, build_task_state
from agent.controller import decide_next_action
from agent.executor import execute_action
from agent.verifier import verify_action, verify_task_completion

from tools.screen import capture_screen


# --------------------------------------------------
# CONFIGURAZIONE MODIFICABILE
# --------------------------------------------------

# Scrivi qui il prompt da eseguire automaticamente.
# Se lasci la stringa vuota (""), il programma te lo chiederà
# nel terminale quando lo avvii.

DEFAULT_INSTRUCTION = "Crea sul Desktop una cartella chiamata PROVA_GUI_AGENT."

MAX_ITERATIONS = 30
MAX_RECENT_ACTIONS = 10

# DEBUG:
# True  = mostra decisioni, parametri, risultati ed errori
# False = disattiva i messaggi di debug aggiuntivi

DEBUG = True

# Screenshot:
# True = salva uno screenshot quando si verifica un errore
# False = non salva screenshot in caso di errore

SAVE_SCREENSHOTS_ON_ERROR = True

# True = salva uno screenshot prima di ogni decisione
# Attenzione: può occupare molto spazio nel tempo.

SAVE_SCREENSHOTS_EACH_STEP = False


# --------------------------------------------------
# CARTELLE E LOG
# --------------------------------------------------

LOG_DIR = Path("logs")
TASK_LOG_DIR = LOG_DIR / "tasks"
SCREENSHOT_DIR = LOG_DIR / "screenshots"

LOG_DIR.mkdir(exist_ok=True)
TASK_LOG_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / "gui_agent.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("GUI_AGENT")


# --------------------------------------------------
# GESTIONE REPORT JSON
# --------------------------------------------------

class TaskLogger:

    def __init__(self, task_id, instruction):

        self.task_id = task_id
        self.instruction = instruction

        self.started_at = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        self.events = []
        self.status = "running"
        self.result = None

    def event(self, event_name, **details):

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "event": event_name,
            **details
        }

        self.events.append(entry)

        logger.info(
            json.dumps(
                entry,
                ensure_ascii=False,
                default=str
            )
        )

        if DEBUG:

            print(f"\n[DEBUG] {event_name}")

            if details:
                print(
                    json.dumps(
                        details,
                        indent=2,
                        ensure_ascii=False,
                        default=str
                    )
                )

    def finish(self, status, result):

        self.status = status
        self.result = result

        self.finished_at = datetime.now().astimezone().isoformat(
            timespec="seconds"
        )

        self.save()

    def save(self):

        report = {
            "task_id": self.task_id,
            "instruction": self.instruction,
            "started_at": self.started_at,
            "finished_at": getattr(self, "finished_at", None),
            "status": self.status,
            "result": self.result,
            "events": self.events
        }

        path = TASK_LOG_DIR / f"task_{self.task_id}.json"

        path.write_text(
            json.dumps(
                report,
                indent=2,
                ensure_ascii=False,
                default=str
            ),
            encoding="utf-8"
        )


# --------------------------------------------------
# SCREENSHOT
# --------------------------------------------------

def save_screenshot(screenshot, task_id, label):

    if not isinstance(screenshot, dict):
        return None

    image = screenshot.get("image")

    if image is None:
        return None

    safe_label = "".join(
        char if char.isalnum() or char in ("-", "_") else "_"
        for char in label
    )

    timestamp = datetime.now().strftime("%H%M%S_%f")

    folder = SCREENSHOT_DIR / task_id
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{timestamp}_{safe_label}.png"

    image.save(path)

    return str(path)


def debug_print(message, data=None):

    if not DEBUG:
        return

    print(f"\n[DEBUG] {message}")

    if data is not None:

        print(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str
            )
        )


# --------------------------------------------------
# FUNZIONI DI SUPPORTO
# --------------------------------------------------

def extract_json(content):

    if not isinstance(content, str) or not content.strip():
        raise ValueError("La risposta del modello è vuota")

    content = content.strip()

    if content.startswith("```"):

        lines = content.splitlines()

        if lines and lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]

        content = "\n".join(lines).strip()

    try:

        return json.loads(content)

    except json.JSONDecodeError as exc:

        raise ValueError(
            f"Il modello non ha restituito JSON valido: {exc}"
        ) from exc


def show_plan(plan):

    print("\n========== PIANO ==========")

    print("Obiettivo:", plan["goal"])

    for index, step in enumerate(plan["steps"], start=1):

        print(
            f'{index}. {step["action"]}: '
            f'{step["description"]}'
        )

    print("===========================\n")


# --------------------------------------------------
# VERIFICA FINALE DEL TASK
# --------------------------------------------------

def verify_plan_criteria(plan, screenshot):

    """
    Chiede al modello visivo di valutare i criteri
    sullo screenshot corrente.

    Un criterio è verificato solo se il modello
    restituisce esplicitamente true.
    """

    criteria = plan["success_criteria"]

    if not criteria:

        return {
            "completed": False,
            "reason": "Il piano non contiene criteri di successo",
            "criterion_results": {}
        }

    image_base64 = screenshot.get("image_base64")

    if not isinstance(image_base64, str) or not image_base64:

        raise ValueError(
            "Immagine necessaria per la verifica mancante"
        )

    prompt = f"""
Sei il Verificatore visivo di un GUI Agent.

Devi controllare esclusivamente ciò che è dimostrabile
dallo screenshot allegato.

CRITERI DA VERIFICARE:
{json.dumps(criteria, ensure_ascii=False)}

REGOLE:
1. Non presumere che un'azione sia riuscita solo perché è stata eseguita.
2. Non inventare elementi o informazioni non visibili.
3. Se un criterio non è chiaramente dimostrabile, assegna false.
4. Valuta ogni criterio separatamente.
5. Non dichiarare completato il task se anche un solo criterio
   non è verificato.

Restituisci esclusivamente JSON valido nel formato:

{{
    "criterion_results": {{
        "testo esatto del criterio": true
    }},
    "reason": "Motivazione sintetica"
}}
"""

    response = ask_llm(
        model=VISION_MODEL,
        messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Verifica i criteri sullo screenshot."
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
        ],
        temperature=0,
        max_tokens=700
    )

    result = extract_json(response["content"])

    criterion_results = result.get("criterion_results")

    if not isinstance(criterion_results, dict):

        raise ValueError(
            "La verifica non contiene criterion_results validi"
        )

    checked_results = {}

    for criterion in criteria:

        value = criterion_results.get(criterion)

        checked_results[criterion] = value is True

    completion = verify_task_completion(
        success_criteria=criteria,
        criterion_results=checked_results
    )

    return {
        **completion,
        "criterion_results": checked_results,
        "reason": result.get(
            "reason",
            completion["reason"]
        )
    }


# --------------------------------------------------
# ESECUZIONE DEL TASK
# --------------------------------------------------

def run_task(instruction):

    task_id = str(uuid.uuid4())

    task_log = TaskLogger(
        task_id,
        instruction
    )

    print("\nAvvio GUI Agent...")
    print("Task ID:", task_id)

    task_log.event(
        "task_started",
        instruction=instruction
    )

    try:

        result = _run_task_loop(
            instruction,
            task_id,
            task_log
        )

        if task_log.result is None:

            task_log.result = result

            task_log.status = result.get(
                "status",
                "finished"
            )

        return result

    except KeyboardInterrupt:

        result = {
            "success": False,
            "status": "interrupted",
            "task_id": task_id
        }

        task_log.status = "interrupted"
        task_log.result = result

        task_log.event("task_interrupted")

        return result

    except Exception as exc:

        logger.exception(
            "Errore generale durante il task"
        )

        result = {
            "success": False,
            "status": "error",
            "task_id": task_id,
            "error": str(exc)
        }

        task_log.status = "error"
        task_log.result = result

        task_log.event(
            "task_error",
            error=str(exc)
        )

        return result

    finally:

        task_log.finish(
            task_log.status,
            task_log.result
        )


# --------------------------------------------------
# CICLO AUTONOMO
# --------------------------------------------------

def _run_task_loop(instruction, task_id, task_log):

    # 1. PLANNER

    print("\n[PLANNER] Creazione del piano...")

    task_log.event("planner_started")

    plan = create_plan(instruction)

    task_log.event(
        "plan_created",
        plan=plan
    )

    if plan["needs_clarification"]:

        question = plan["clarification_question"]

        print("\n[PLANNER] Serve un chiarimento:")
        print(question)

        result = {
            "success": False,
            "status": "needs_clarification",
            "question": question,
            "task_id": task_id
        }

        task_log.status = "needs_clarification"
        task_log.result = result

        task_log.event(
            "clarification_requested",
            question=question
        )

        return result

    task_state = build_task_state(
        instruction,
        plan
    )

    task_state.task_id = task_id
    task_state.status = "running"

    show_plan(plan)

    recent_actions = []

    # 2. CICLO DEL CONTROLLER

    for iteration in range(1, MAX_ITERATIONS + 1):

        print(
            f"\n========== ITERAZIONE {iteration} =========="
        )

        # SCREENSHOT

        print("[SCREEN] Acquisizione dello schermo...")

        screenshot = capture_screen()

        if SAVE_SCREENSHOTS_EACH_STEP:

            path = save_screenshot(
                screenshot,
                task_id,
                f"iteration_{iteration}_before"
            )

            task_log.event(
                "screenshot_saved",
                path=path,
                iteration=iteration
            )

        # CONTROLLER

        print("[CONTROLLER] Analisi della GUI...")

        decision = decide_next_action(
            instruction=instruction,
            plan=plan,
            task_state=task_state,
            recent_actions=recent_actions,
            screenshot=screenshot
        )

        action = decision["action"]
        parameters = decision["parameters"]

        print(
            "[CONTROLLER] Azione scelta:",
            action
        )

        print(
            "[CONTROLLER] Motivo:",
            decision["short_reason"]
        )

        task_log.event(
            "controller_decision",
            iteration=iteration,
            action=action,
            parameters=parameters,
            short_reason=decision["short_reason"],
            decision=decision
        )

        # RICHIESTA DI CHIARIMENTO

        if decision["needs_clarification"]:

            question = decision["clarification_question"]

            print("\n[AGENT] Serve un chiarimento:")
            print(question)

            task_state.status = "needs_clarification"

            result = {
                "success": False,
                "status": "needs_clarification",
                "question": question,
                "task_id": task_id
            }

            task_log.status = "needs_clarification"
            task_log.result = result

            task_log.event(
                "clarification_requested",
                question=question
            )

            return result

        # 3. VERIFICA FINALE

        if action == "verify":

            print(
                "[VERIFIER] Verifica visiva dei criteri..."
            )

            try:

                result = verify_plan_criteria(
                    plan=plan,
                    screenshot=screenshot
                )

            except Exception as exc:

                print(
                    "[VERIFIER] Errore durante la verifica:",
                    exc
                )

                screenshot_path = None

                if SAVE_SCREENSHOTS_ON_ERROR:

                    screenshot_path = save_screenshot(
                        screenshot,
                        task_id,
                        f"iteration_{iteration}_verification_error"
                    )

                task_log.event(
                    "verification_error",
                    iteration=iteration,
                    error=str(exc),
                    screenshot=screenshot_path
                )

                recent_actions.append({
                    "action": "verify",
                    "result": "verification_error",
                    "error": str(exc)
                })

                recent_actions = recent_actions[
                    -MAX_RECENT_ACTIONS:
                ]

                continue

            print(
                "[VERIFIER] Risultato:",
                result
            )

            task_log.event(
                "task_verification",
                iteration=iteration,
                result=result
            )

            if result["completed"]:

                task_state.status = "completed"

                task_state.completed_at = datetime.now().isoformat()

                for step in task_state.steps:
                    step.status = "completed"

                print(
                    "\n[AGENT] Task completato e verificato."
                )

                final_result = {
                    "success": True,
                    "status": "completed",
                    "task_id": task_id,
                    "verification": result
                }

                task_log.status = "completed"
                task_log.result = final_result

                task_log.event(
                    "task_completed",
                    verification=result
                )

                return final_result

            print(
                "[VERIFIER] Completamento non confermato. "
                "Il Controller potrà proseguire."
            )

            recent_actions.append({
                "action": "verify",
                "result": "verification_pending",
                "verification": result
            })

            recent_actions = recent_actions[
                -MAX_RECENT_ACTIONS:
            ]

            continue

        # 4. EXECUTOR

        print(
            "[EXECUTOR] Esecuzione dell'azione..."
        )

        try:

            execution_result = execute_action(
                decision
            )

        except Exception as exc:

            print(
                "[EXECUTOR] Errore:",
                exc
            )

            verification = verify_action(
                decision=decision,
                execution_result={
                    "success": False,
                    "message": str(exc)
                }
            )

            screenshot_path = None

            if SAVE_SCREENSHOTS_ON_ERROR:

                screenshot_path = save_screenshot(
                    screenshot,
                    task_id,
                    f"iteration_{iteration}_action_error"
                )

            task_log.event(
                "execution_error",
                iteration=iteration,
                action=action,
                parameters=parameters,
                error=str(exc),
                verification=verification,
                screenshot=screenshot_path
            )

            recent_actions.append({
                "action": action,
                "parameters": parameters,
                "result": "error",
                "error": str(exc)
            })

            recent_actions = recent_actions[
                -MAX_RECENT_ACTIONS:
            ]

            continue

        print(
            "[EXECUTOR] Risultato:",
            execution_result
        )

        # 5. VERIFIER DELL'AZIONE

        verification = verify_action(
            decision=decision,
            execution_result=execution_result,
            observation=None
        )

        print(
            "[VERIFIER] Stato:",
            verification["status"]
        )

        task_log.event(
            "action_executed",
            iteration=iteration,
            action=action,
            parameters=parameters,
            execution_result=execution_result,
            verification=verification
        )

        recent_actions.append({
            "action": action,
            "parameters": parameters,
            "execution_result": execution_result,
            "verification": verification["status"],
            "reason": verification["reason"]
        })

        recent_actions = recent_actions[
            -MAX_RECENT_ACTIONS:
        ]

    # 6. LIMITE ITERAZIONI

    task_state.status = "failed"

    task_state.error = (
        "Limite massimo di iterazioni raggiunto"
    )

    print(
        "\n[AGENT] Limite massimo di iterazioni raggiunto."
    )

    result = {
        "success": False,
        "status": "iteration_limit",
        "task_id": task_id
    }

    task_log.status = "iteration_limit"
    task_log.result = result

    task_log.event(
        "iteration_limit_reached",
        iterations=MAX_ITERATIONS
    )

    return result


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    try:

        validate_config()

        print("\n================================")
        print("           GUI AGENT")
        print("================================")

        # Se DEFAULT_INSTRUCTION contiene testo,
        # usa direttamente quel prompt.
        #
        # Se è vuoto, chiede il prompt nel terminale.

        if DEFAULT_INSTRUCTION.strip():

            instruction = DEFAULT_INSTRUCTION.strip()

            print("\nPrompt preimpostato nel main.py:")
            print(">", instruction)

        else:

            instruction = input(
                "\nCosa vuoi che faccia il computer?\n> "
            ).strip()

        if not instruction:

            print("Istruzione vuota. Nessun task avviato.")
            return

        result = run_task(instruction)

        print("\n========== RISULTATO ==========")

        print(
            json.dumps(
                result,
                indent=4,
                ensure_ascii=False
            )
        )

        print("================================")

    except KeyboardInterrupt:

        print(
            "\n[AGENT] Interruzione richiesta dall'utente."
        )

    except Exception as exc:

        logger.exception("Errore generale")

        print("\n[ERRORE]", exc)


if __name__ == "__main__":
    main()
