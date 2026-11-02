
from tools.computer import (
    click_bbox,
    type_text,
    press_key,
    hotkey,
    scroll,
    wait_seconds
)

from agent.actions import (
    EXECUTABLE_ACTIONS,
    validate_executable_action
)


def execute_action(decision):
    """
    Esegue una singola azione GUI autorizzata dal Controller.

    Non esegue codice o comandi arbitrari.
    Le richieste di verifica sono gestite separatamente dal Verifier.
    """

    if not isinstance(decision, dict):
        raise ValueError("Decisione non valida")

    action = decision.get("action")
    parameters = decision.get("parameters", {})

    if not isinstance(action, str):
        raise ValueError("Azione non valida")

    if action == "verify":
        raise ValueError(
            "L'azione verify deve essere gestita dal Verifier, "
            "non dall'Executor"
        )

    if not validate_executable_action(action):
        raise ValueError(
            f"Azione non consentita o non eseguibile: {action}"
        )

    if action not in EXECUTABLE_ACTIONS:
        raise ValueError(
            f"Azione non implementata: {action}"
        )

    if not isinstance(parameters, dict):
        raise ValueError("Parametri non validi")

    if action == "click":
        return click_bbox(
            parameters.get("bbox"),
            button="left"
        )

    elif action == "double_click":
        return click_bbox(
            parameters.get("bbox"),
            button="left",
            clicks=2
        )

    elif action == "right_click":
        return click_bbox(
            parameters.get("bbox"),
            button="right"
        )

    elif action == "type_text":
        return type_text(parameters.get("text"))

    elif action == "press_key":
        return press_key(parameters.get("key"))

    elif action == "hotkey":
        return hotkey(parameters.get("keys"))

    elif action == "scroll":
        return scroll(parameters.get("amount"))

    elif action == "wait":
        return wait_seconds(parameters.get("seconds", 1))

    raise RuntimeError(f"Azione non gestita: {action}")
