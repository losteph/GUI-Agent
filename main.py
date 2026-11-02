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
# CONFIGURAZIONE
# --------------------------------------------------

MAX_ITERATIONS = 30
MAX_RECENT_ACTIONS = 10

Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    filename="logs/gui_agent.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("GUI_AGENT")


# --------------------------------------------------
# FUNZIONI DI SUPPORTO
# --------------------------------------------------

def save_log(data):
    logger.info(json.dumps(data, ensure_ascii=False, default=str))


def extract_json(content):
    if not isinstance(content, str) or not content.strip():
        raise ValueError("La risposta del modello è vuota")

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


def verify_plan_criteria(plan, screenshot):
    """
    Chiede al modello visivo di valutare i criteri
    sullo screenshot corrente.

    Un criterio è verificato solo se il modello restituisce
    esplicitamente true.
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
        raise ValueError("Immagine necessaria per la verifica mancante")

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

    # Costruiamo un risultato controllato:
    # criteri mancanti o con valori non booleani diventano False.
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
        "reason": result.get("reason", completion["reason"])
    }


# --------------------------------------------------
# ESECUZIONE DEL TASK
# --------------------------------------------------

def run_task(instruction):

    task_id = str(uuid.uuid4())

    print("\nAvvio GUI Agent...")
    print("Task ID:", task_id)

    save_log({
        "event": "task_started",
        "task_id": task_id,
        "instruction": instruction
    })

    # 1. PLANNER

    print("\n[PLANNER] Creazione del piano...")

    plan = create_plan(instruction)

    if plan["needs_clarification"]:
        question = plan["clarification_question"]

        print("\n[PLANNER] Serve un chiarimento:")
        print(question)

        return {
            "success": False,
            "status": "needs_clarification",
            "question": question,
            "task_id": task_id
        }

    task_state = build_task_state(instruction, plan)
    task_state.task_id = task_id
    task_state.status = "running"

    show_plan(plan)

    recent_actions = []

    # 2. CICLO AUTONOMO

    for iteration in range(1, MAX_ITERATIONS + 1):

        print(f"\n========== ITERAZIONE {iteration} ==========")

        # Acquisizione screenshot

        print("[SCREEN] Acquisizione dello schermo...")

        screenshot = capture_screen()

        # Controller

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

        print("[CONTROLLER] Azione scelta:", action)
        print("[CONTROLLER] Motivo:", decision["short_reason"])

        save_log({
            "event": "controller_decision",
            "task_id": task_id,
            "iteration": iteration,
            "decision": decision
        })

        # Richiesta di chiarimento

        if decision["needs_clarification"]:
            question = decision["clarification_question"]

            print("\n[AGENT] Serve un chiarimento:")
            print(question)

            task_state.status = "needs_clarification"

            return {
                "success": False,
                "status": "needs_clarification",
                "question": question,
                "task_id": task_id
            }

        # 3. VERIFICA DEL TASK

        if action == "verify":

            print("[VERIFIER] Verifica visiva dei criteri...")

            try:
                result = verify_plan_criteria(
                    plan=plan,
                    screenshot=screenshot
                )

            except Exception as exc:
                print("[VERIFIER] Errore durante la verifica:", exc)

                save_log({
                    "event": "verification_error",
                    "task_id": task_id,
                    "error": str(exc)
                })

                recent_actions.append({
                    "action": "verify",
                    "result": "verification_error",
                    "error": str(exc)
                })

                recent_actions = recent_actions[-MAX_RECENT_ACTIONS:]
                continue

            print("[VERIFIER] Risultato:", result)

            save_log({
                "event": "task_verification",
                "task_id": task_id,
                "result": result
            })

            if result["completed"]:

                task_state.status = "completed"
                task_state.completed_at = datetime.now().isoformat()

                for step in task_state.steps:
                    step.status = "completed"

                print("\n[AGENT] Task completato e verificato.")

                save_log({
                    "event": "task_completed",
                    "task_id": task_id,
                    "result": result
                })

                return {
                    "success": True,
                    "status": "completed",
                    "task_id": task_id,
                    "verification": result
                }

            print(
                "[VERIFIER] Completamento non confermato. "
                "Il Controller potrà proseguire."
            )

            recent_actions.append({
                "action": "verify",
                "result": "verification_pending",
                "verification": result
            })

            recent_actions = recent_actions[-MAX_RECENT_ACTIONS:]
            continue

        # 4. EXECUTOR

        print("[EXECUTOR] Esecuzione dell'azione...")

        try:
            execution_result = execute_action(decision)

        except Exception as exc:

            print("[EXECUTOR] Errore:", exc)

            verification = verify_action(
                decision=decision,
                execution_result={
                    "success": False,
                    "message": str(exc)
                }
            )

            recent_actions.append({
                "action": action,
                "parameters": parameters,
                "verification": verification
            })

            recent_actions = recent_actions[-MAX_RECENT_ACTIONS:]

            save_log({
                "event": "execution_error",
                "task_id": task_id,
                "action": action,
                "error": str(exc),
                "verification": verification
            })

            continue

        print("[EXECUTOR] Risultato:", execution_result)

        # 5. VERIFIER DELL'AZIONE

        verification = verify_action(
            decision=decision,
            execution_result=execution_result,
            observation=None
        )

        print("[VERIFIER] Stato:", verification["status"])

        recent_actions.append({
            "action": action,
            "parameters": parameters,
            "execution_result": execution_result,
            "verification": verification["status"],
            "reason": verification["reason"]
        })

        recent_actions = recent_actions[-MAX_RECENT_ACTIONS:]

        save_log({
            "event": "action_verification",
            "task_id": task_id,
            "action": action,
            "execution_result": execution_result,
            "verification": verification
        })

    # 6. LIMITE ITERAZIONI

    task_state.status = "failed"
    task_state.error = "Limite massimo di iterazioni raggiunto"

    print("\n[AGENT] Limite massimo di iterazioni raggiunto.")

    save_log({
        "event": "iteration_limit_reached",
        "task_id": task_id,
        "iterations": MAX_ITERATIONS
    })

    return {
        "success": False,
        "status": "iteration_limit",
        "task_id": task_id
    }


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    try:
        validate_config()

        print("\n================================")
        print("           GUI AGENT")
        print("================================")

        instruction = input(
            "\nCosa vuoi che faccia il computer?\n> "
        ).strip()

        if not instruction:
            print("Istruzione vuota.")
            return

        result = run_task(instruction)

        print("\n========== RISULTATO ==========")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        print("================================")

    except KeyboardInterrupt:
        print("\n[AGENT] Interruzione richiesta dall'utente.")

    except Exception as exc:
        logger.exception("Errore generale")
        print("\n[ERRORE]", exc)


if __name__ == "__main__":
    main()
