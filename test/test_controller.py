
from agent.controller import validate_decision

test_decision = {
    "action": "click",
    "parameters": {
        "target": "New Folder",
        "bbox": [0.10, 0.20, 0.30, 0.40]
    },
    "short_reason": "Il menu mostra New Folder",
    "expected_result": "Apertura della finestra di creazione",
    "requires_verification": True,
    "task_completed": False,
    "needs_clarification": False,
    "clarification_question": None
}

try:
    result = validate_decision(test_decision)
    print("CONTROLLER VALIDATION OK")
    print(result)

except Exception as error:
    print("VALIDATION ERROR:", error)
