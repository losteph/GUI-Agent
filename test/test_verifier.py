
from agent.verifier import (
    verify_action,
    verify_task_completion
)


def test_execution_failure():
    result = verify_action(
        {"requires_verification": True},
        {"success": False, "message": "Click fallito"}
    )

    assert result["status"] == "failed"
    assert result["verified"] is False


def test_needs_observation():
    result = verify_action(
        {"requires_verification": True},
        {"success": True}
    )

    assert result["status"] == "needs_observation"
    assert result["verified"] is False


def test_successful_verification():
    result = verify_action(
        {"requires_verification": True},
        {"success": True},
        {
            "verified": True,
            "reason": "Il file è visibile nella cartella"
        }
    )

    assert result["status"] == "verified"
    assert result["verified"] is True


def test_failed_verification():
    result = verify_action(
        {"requires_verification": True},
        {"success": True},
        {
            "verified": False,
            "reason": "Il file non è stato trovato"
        }
    )

    assert result["status"] == "failed"
    assert result["retry_recommended"] is True


def test_task_completion():
    result = verify_task_completion(
        ["file_created", "file_saved"],
        {
            "file_created": True,
            "file_saved": True
        }
    )

    assert result["completed"] is True


def test_incomplete_task():
    result = verify_task_completion(
        ["file_created", "file_saved"],
        {
            "file_created": True,
            "file_saved": False
        }
    )

    assert result["completed"] is False


def main():
    tests = [
        test_execution_failure,
        test_needs_observation,
        test_successful_verification,
        test_failed_verification,
        test_task_completion,
        test_incomplete_task
    ]

    passed = 0

    print("================================")
    print("       TEST VERIFIER")
    print("================================")

    for test in tests:
        try:
            test()
            print(f"OK: {test.__name__}")
            passed += 1
        except Exception as error:
            print(f"ERRORE: {test.__name__}: {error}")

    print("--------------------------------")
    print(f"RISULTATO: {passed}/{len(tests)} test superati")
    print("================================")


if __name__ == "__main__":
    main()
