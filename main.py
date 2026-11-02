
import json
import logging
import uuid

from datetime import datetime

from config import validate_config

from agent.planner import create_plan, build_task_state
from agent.controller import decide_next_action
from agent.executor import execute_action
from agent.verifier import verify_action, verify_task_completion

from tools.screen import capture_screen


# --------------------------------------------------
# CONFIGURAZIONE
# --------------------------------------------------

MAX_ITERATIONS = 30

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
    """Registra un evento nel log."""

    logger.info(
        json.dumps(data, ensure_ascii=False, default=str)
    )


def show_plan(plan):
    """Mostra il piano generato dal Planner."""

    print("\n========== PIANO ==========")
    print("Obiettivo:", plan["goal"])

    for step in plan["steps"]:
        print(
            f'{step["id"] if "id" in step else ""} '
            f'- {step["action"]}: {step["description"]}'
        )

    print("===========================\n")


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
            "question": question
        }

    task_state = build_task_state(instruction, plan)

    show_plan(plan)

    recent_actions = []
    iteration = 0

    # 2. CICLO AUTONOMO

    while iteration < MAX_ITERATIONS:

        iteration += 1

        print(f"\n========== ITERAZIONE {iteration} ==========")

        # Acquisizione dello screenshot

        print("[SCREEN] Acquisizione dello schermo...")

        screenshot = capture_screen()

        # Controller: decide la prossima azione

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

        # Gestione chiarimenti

        if decision["needs_clarification"]:
            question = decision["clarification_question"]

            print("\n[AGENT] Serve un chiarimento:")
            print(question)

            return {
                "success": False,
                "status": "needs_clarification",
                "question": question
            }

        # 3. RICHIESTA DI VERIFICA

        if action == "verify":

            print("[VERIFIER] Richiesta di verifica...")

            criteria = plan["success_criteria"]

            print(
                "[VERIFIER] I criteri di successo richiedono "
                "una verifica indipendente."
            )

            result = verify_task_completion(
                success_criteria=criteria,
                criterion_results={}
            )

            if result.get("verified") is True:
                task_state.status = "completed"
                task_state.completed_at = datetime.now().isoformat()

                return {
                    "success": True,
                    "status": "completed",
                    "task_id": task_id
                }

            print(
                "[VERIFIER] Non ci sono ancora prove sufficienti "
                "per confermare il completamento."
            )

            save_log({
                "event": "verification_pending",
                "task_id": task_id,
                "criteria": criteria,
                "result": result
            })

            # Non dichiariamo il task completato.
            # Lasciamo al Controller la possibilità di proseguire.
            recent_actions.append({
                "action": "verify",
                "result": "verification_pending"
            })

            continue

        # 4. EXECUTOR

        print("[EXECUTOR] Esecuzione dell'azione...")

        try:
            execution_result = execute_action(decision)

        except Exception as exc:

            print("[EXECUTOR] Errore:", exc)

            save_log({
                "event": "execution_error",
                "task_id": task_id,
                "action": action,
                "error": str(exc)
            })

            recent_actions.append({
                "action": action,
                "result": "error",
                "error": str(exc)
            })

            continue

        print("[EXECUTOR] Risultato:", execution_result)

        save_log({
            "event": "action_executed",
            "task_id": task_id,
            "action": action,
            "result": execution_result
        })

        # 5. VERIFIER

        verification = verify_action(
            decision=decision,
            execution_result=execution_result,
            observation=None
        )

        print(
            "[VERIFIER] Stato:",
            verification["status"]
        )

        recent_actions.append({
            "action": action,
            "parameters": parameters,
            "execution_result": execution_result,
            "verification": verification["status"]
        })

        save_log({
            "event": "verification",
            "task_id": task_id,
            "action": action,
            "result": verification
        })

        # 6. AGGIORNAMENTO STATO

        if (
            verification["status"] == "failed"
            and verification.get("retry") is False
        ):
            print("[AGENT] Azione non verificata.")

        # Il Controller rivaluterà lo stato reale
        # attraverso il prossimo screenshot.

    # 7. LIMITE ITERAZIONI

    task_state.status = "failed"
    task_state.error = "Limite massimo di iterazioni raggiunto"

    print("\n[AGENT] Limite massimo di iterazioni raggiunto.")

    save_log({
        "event": "iteration_limit_reached",
        "task_id": task_id,
        "iterations": iteration
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
        print("       GUI AGENT")
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
