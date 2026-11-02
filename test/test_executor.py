
from agent.executor import execute_action


def test_unauthorized_action():
    print("\n[Test 1] Azione non autorizzata")

    try:
        execute_action({
            "action": "create_folder",
            "parameters": {
                "path": "/tmp/test"
            }
        })
    except Exception:
        print("OK: azione non autorizzata bloccata")
        return

    raise AssertionError("L'azione non autorizzata è stata accettata")


def test_invalid_coordinates():
    print("\n[Test 2] Coordinate non valide")

    try:
        execute_action({
            "action": "click",
            "parameters": {
                "bbox": [1.5, 0.2, 1.8, 0.5]
            }
        })
    except Exception:
        print("OK: coordinate non valide bloccate")
        return

    raise AssertionError("Le coordinate non valide sono state accettate")


def test_unicode_text():
    print("\n[Test 3] Testo Unicode")

    try:
        execute_action({
            "action": "type_text",
            "parameters": {
                "text": "Città"
            }
        })
    except Exception:
        print("OK: testo Unicode rifiutato")
        return

    raise AssertionError("Il testo Unicode è stato accettato")


def main():
    print("================================")
    print("       TEST EXECUTOR")
    print("================================")

    tests = [
        test_unauthorized_action,
        test_invalid_coordinates,
        test_unicode_text
    ]

    passed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as error:
            print(f"ERRORE: {error}")

    print("\n================================")
    print(f"RISULTATO: {passed}/{len(tests)} test superati")
    print("================================")


if __name__ == "__main__":
    main()
