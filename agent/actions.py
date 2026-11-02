
# agent/actions.py

# Azioni di alto livello utilizzabili dal Planner.
# Descrivono COSA deve essere fatto, non come farlo.
PLANNER_ACTIONS = {
    "open_application",
    "create_folder",
    "open_folder",
    "create_file",
    "write_text",
    "save_file",
    "close_window",
}

# Azioni concrete utilizzabili dal Controller.
# Descrivono COME interagire con la GUI.
CONTROLLER_ACTIONS = {
    "click",
    "double_click",
    "right_click",
    "press_key",
    "hotkey",
    "type_text",
    "scroll",
    "wait",
    "verify",
}

# Azioni che l'Executor può effettivamente eseguire.
EXECUTABLE_ACTIONS = {
    "click",
    "double_click",
    "right_click",
    "press_key",
    "hotkey",
    "type_text",
    "scroll",
    "wait",
}

# Azioni per cui il risultato deve essere verificato.
ACTIONS_REQUIRING_VERIFICATION = {
    "open_application",
    "create_folder",
    "open_folder",
    "create_file",
    "write_text",
    "save_file",
    "close_window",
}


def validate_planner_action(action: str) -> bool:
    return action in PLANNER_ACTIONS


def validate_controller_action(action: str) -> bool:
    return action in CONTROLLER_ACTIONS


def validate_executable_action(action: str) -> bool:
    return action in EXECUTABLE_ACTIONS
