
import os
import time

# Connessione al display della VM Lubuntu via SSH.
os.environ.setdefault("DISPLAY", ":0")
os.environ.setdefault("XAUTHORITY", "/home/ste/.Xauthority")

import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25

# Limiti di sicurezza.
MAX_SCROLL_AMOUNT = 10
MAX_TYPE_LENGTH = 5000
MAX_WAIT_SECONDS = 10

# Tasti ammessi: impediamo combinazioni arbitrarie.
ALLOWED_KEYS = {
    "enter", "esc", "tab", "space", "backspace", "delete",
    "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown",
    "ctrl", "alt", "shift", "win",
    "f1", "f2", "f3", "f4", "f5",
    "f6", "f7", "f8", "f9", "f10", "f11", "f12",
    "a", "c", "v", "x", "z", "s", "n", "o", "w"
}


def get_screen_size():
    size = pyautogui.size()
    return size.width, size.height


def normalized_bbox_to_point(bbox):
    """
    Converte un bounding box normalizzato nel punto centrale
    dello schermo reale.
    """
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        raise ValueError("Bounding box non valido")

    if not all(
        isinstance(v, (int, float)) and 0 <= v <= 1
        for v in bbox
    ):
        raise ValueError("Coordinate non valide")

    x1, y1, x2, y2 = bbox

    if x1 >= x2 or y1 >= y2:
        raise ValueError("Bounding box con dimensioni non valide")

    width, height = get_screen_size()

    x = round(((x1 + x2) / 2) * width)
    y = round(((y1 + y2) / 2) * height)

    x = max(0, min(x, width - 1))
    y = max(0, min(y, height - 1))

    return x, y


def click_bbox(bbox, button="left", clicks=1):
    if button not in {"left", "right", "middle"}:
        raise ValueError("Pulsante mouse non consentito")

    if clicks not in {1, 2}:
        raise ValueError("Numero di click non consentito")

    x, y = normalized_bbox_to_point(bbox)

    pyautogui.click(
        x=x,
        y=y,
        button=button,
        clicks=clicks,
        interval=0.15
    )

    return {
        "success": True,
        "action": "click",
        "position": [x, y]
    }


def move_mouse(bbox):
    x, y = normalized_bbox_to_point(bbox)
    pyautogui.moveTo(x, y, duration=0.2)

    return {"success": True, "position": [x, y]}


def type_text(text):
    if not isinstance(text, str):
        raise ValueError("Il testo deve essere una stringa")

    if len(text) > MAX_TYPE_LENGTH:
        raise ValueError("Testo troppo lungo")

    # pyautogui.write è adatto principalmente al testo ASCII.
    # Per Unicode useremo in seguito una gestione clipboard dedicata.
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError(
            "Testo non ASCII: supporto Unicode da configurare"
        )

    pyautogui.write(text, interval=0.02)

    return {
        "success": True,
        "characters_typed": len(text)
    }


def press_key(key):
    if not isinstance(key, str):
        raise ValueError("Tasto non valido")

    key = key.lower().strip()

    if key not in ALLOWED_KEYS:
        raise ValueError(f"Tasto non consentito: {key}")

    pyautogui.press(key)

    return {"success": True, "key": key}


def hotkey(keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("Combinazione di tasti non valida")

    normalized = [str(k).lower().strip() for k in keys]

    if len(normalized) > 3:
        raise ValueError("Combinazione troppo lunga")

    if not all(k in ALLOWED_KEYS for k in normalized):
        raise ValueError("Combinazione contiene tasti non consentiti")

    pyautogui.hotkey(*normalized)

    return {"success": True, "keys": normalized}


def scroll(amount):
    if not isinstance(amount, int):
        raise ValueError("Scroll deve essere un numero intero")

    if not -MAX_SCROLL_AMOUNT <= amount <= MAX_SCROLL_AMOUNT:
        raise ValueError("Scroll oltre il limite consentito")

    pyautogui.scroll(amount)

    return {"success": True, "amount": amount}


def wait_seconds(seconds):
    if not isinstance(seconds, (int, float)):
        raise ValueError("Durata non valida")

    if not 0 <= seconds <= MAX_WAIT_SECONDS:
        raise ValueError("Attesa oltre il limite consentito")

    time.sleep(seconds)

    return {"success": True, "waited": seconds}


def capture_screen():
    return pyautogui.screenshot()
