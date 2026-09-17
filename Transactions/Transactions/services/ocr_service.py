import os
import shutil

import pytesseract

from PIL import Image


# On Windows, the Tesseract engine (a separate binary from the
# pytesseract Python wrapper) isn't always on PATH, even once
# installed - point at it explicitly if we can find it, so uploads
# don't fail with "tesseract is not installed or it's not in your PATH".
_DEFAULT_WINDOWS_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

_tesseract_cmd = (
    os.getenv("TESSERACT_CMD")
    or shutil.which("tesseract")
    or (
        _DEFAULT_WINDOWS_PATH
        if os.path.isfile(_DEFAULT_WINDOWS_PATH)
        else None
    )
)

if _tesseract_cmd:
    pytesseract.pytesseract.tesseract_cmd = _tesseract_cmd


def extract_text_from_image(image_path):

    image = Image.open(
        image_path
    )


    text = pytesseract.image_to_string(
        image
    )


    # Many UPI apps put the transaction date/time in a solid-color
    # header banner (e.g. PhonePe's green "Transaction Successful"
    # bar). That trips up Tesseract's automatic page-layout detection
    # on the full screenshot often enough that the date/time silently
    # goes missing - a second pass on just that region, told to expect
    # one uniform block of text instead of guessing the layout, reads
    # it far more reliably. Cheap enough to always run.
    header_text = _extract_header_text(image)

    if header_text.strip():
        text = f"{header_text}\n{text}"


    return text


def _extract_header_text(image):

    try:

        width, height = image.size

        header = image.crop(
            (0, 0, width, int(height * 0.15))
        )

        return pytesseract.image_to_string(
            header,
            config="--psm 6"
        )

    except Exception:

        # Header OCR is a bonus pass - if it fails for any reason,
        # fall back to whatever the full-image pass already found.
        return ""