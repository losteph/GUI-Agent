
import json
from unittest.mock import patch

from agent.planner import (
    extract_json,
    validate_plan,
    create_plan,
    build_task_state
)


MOCK_PLAN = {
    "goal": "Create a folder named Progetti",
    "needs_clarification": False,
    "clarification_question": None,
    "steps": [
        {
            "action": "create_folder",
            "description": "Create the folder Progetti",
            "parameters": {
                "name": "Progetti"
            }
        }
    ],
    "success_criteria": [
        "The folder Progetti exists"
    ]
}


def test_extract_json():
    content = json.dumps(MOCK_PLAN)

    result = extract_json(content)

    assert result["goal"] == MOCK_PLAN["goal"]
    print("OK: JSON estratto correttamente")


def test_extract_json_with_markdown():
    content = "```json\n" + json.dumps(MOCK_PLAN) + "\n```"

    result = extract_json(content)

    assert result["goal"] == MOCK_PLAN["goal"]
    print("OK: JSON estratto da Markdown")


def test_validate_plan():
    validate_plan(MOCK_PLAN)
    print("OK: piano valido accettato")


def test_reject_invalid_action():
    invalid_plan = json.loads(json.dumps(MOCK_PLAN))
    invalid_plan["steps"][0]["action"] = "delete_everything"

    try:
        validate_plan(invalid_plan)
    except (ValueError, TypeError):
        print("OK: azione non autorizzata rifiutata")
        return

    raise AssertionError("Il Planner ha accettato un'azione non autorizzata")


def test_create_plan_without_api():
    fake_response = {
        "content": json.dumps(MOCK_PLAN),
        "model": "mock-model",
        "usage": None
    }

    with patch("agent.planner.ask_llm", return_value=fake_response) as mock_llm:
        result = create_plan("Create a folder named Progetti")

        mock_llm.assert_called_once()

    assert result["goal"] == MOCK_PLAN["goal"]
    assert len(result["steps"]) == 1

    print("OK: Planner testato con risposta simulata")


def test_build_task_state():
    state = build_task_state(
        "Create a folder named Progetti",
        MOCK_PLAN
    )

    assert state.goal == MOCK_PLAN["goal"]
    assert len(state.steps) == 1
    assert state.steps[0].action == "create_folder"
    assert state.steps[0].status == "pending"

    print("OK: TaskState costruito correttamente")


def main():
    tests = [
        test_extract_json,
        test_extract_json_with_markdown,
        test_validate_plan,
        test_reject_invalid_action,
        test_create_plan_without_api,
        test_build_task_state
    ]

    passed = 0

    print("================================")
    print("        TEST PLANNER")
    print("================================")

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            print(f"ERRORE in {test.__name__}: {error}")

    print("--------------------------------")
    print(f"RISULTATO: {passed}/{len(tests)} test superati")
    print("================================")


if __name__ == "__main__":
    main()
