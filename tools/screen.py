
import os
import io
import base64

# Configurazione display Lubuntu via SSH.
os.environ.setdefault("DISPLAY", ":0")
os.environ.setdefault("XAUTHORITY", "/home/ste/.Xauthority")

import pyautogui
from PIL import Image


def capture_screen(max_width=1280, max_height=900, quality=70):
    """
    Acquisisce lo schermo e restituisce:
    - immagine PIL
    - dimensioni originali
    """

    screenshot = pyautogui.screenshot()
    original_size = screenshot.size

    screenshot.thumbnail((max_width, max_height))

    buffer = io.BytesIO()

    screenshot.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True
    )

    image_bytes = buffer.getvalue()

    image_base64 = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    return {
        "image": screenshot,
        "image_base64": image_base64,
        "original_width": original_size[0],
        "original_height": original_size[1],
        "width": screenshot.width,
        "height": screenshot.height
    }


def get_screen_description():
    """
    Restituisce informazioni essenziali sullo schermo.
    Non utilizza chiamate AI.
    """

    return {
        "width": pyautogui.size().width,
        "height": pyautogui.size().height
    }
