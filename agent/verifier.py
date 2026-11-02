
def verify_action(decision, execution_result, observation=None):
    """
    Verifica l'esito di un'azione.

    execution_result: risultato restituito dall'Executor.
    observation: risultato di un controllo successivo
                (in futuro potrà arrivare dal modello visivo).
    """

    if not isinstance(decision, dict):
        raise ValueError("decision deve essere un dizionario")

    if not isinstance(execution_result, dict):
        raise ValueError("execution_result deve essere un dizionario")

    if execution_result.get("success") is not True:
        return {
            "status": "failed",
            "verified": False,
            "reason": execution_result.get(
                "message", "L'Executor non ha confermato l'esecuzione"
            ),
            "retry_recommended": True
        }

    # Se non è richiesta una verifica ulteriore,
    # registriamo l'esecuzione senza dichiararla verificata.
    if decision.get("requires_verification") is False:
        return {
            "status": "executed",
            "verified": False,
            "reason": "Azione eseguita; verifica ulteriore non richiesta",
            "retry_recommended": False
        }

    # Senza un'osservazione successiva non possiamo
    # sapere se l'obiettivo è stato raggiunto.
    if observation is None:
        return {
            "status": "needs_observation",
            "verified": False,
            "reason": "Serve un controllo del risultato nella GUI",
            "retry_recommended": False
        }

    if not isinstance(observation, dict):
        raise ValueError("observation deve essere un dizionario")

    if not isinstance(observation.get("verified"), bool):
        raise ValueError("observation deve contenere verified: true/false")

    verified = observation["verified"]

    return {
        "status": "verified" if verified else "failed",
        "verified": verified,
        "reason": observation.get(
            "reason",
            "Risultato verificato" if verified else "Risultato non verificato"
        ),
        "retry_recommended": not verified
    }


def verify_task_completion(success_criteria, criterion_results):
    """
    La task è completata solo se tutti i criteri
    hanno un risultato esplicitamente verificato.
    """

    if not isinstance(success_criteria, list):
        raise ValueError("success_criteria deve essere una lista")

    if not isinstance(criterion_results, dict):
        raise ValueError("criterion_results deve essere un dizionario")

    if not success_criteria:
        return {
            "completed": False,
            "reason": "Non sono stati definiti criteri di successo"
        }

    unverified = [
        criterion
        for criterion in success_criteria
        if criterion_results.get(criterion) is not True
    ]

    if unverified:
        return {
            "completed": False,
            "reason": "Alcuni criteri non sono stati verificati",
            "unverified_criteria": unverified
        }

    return {
        "completed": True,
        "reason": "Tutti i criteri di successo sono stati verificati"
    }
