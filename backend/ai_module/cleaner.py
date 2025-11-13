import re
from bs4 import BeautifulSoup

NAVIGATION_PHRASES = [
    "zum inhalt springen",
    "zur hauptnavigation springen",
    "zu weiteren angeboten",
    "please enable javascript",
    "view this video",
]

def clean_html(text: str) -> str:
    """Удаляет HTML, переносы строк, скрипты."""
    try:
        soup = BeautifulSoup(text, "html.parser")
        cleaned = soup.get_text(separator=" ")
    except Exception:
        cleaned = text

    # убираем лишний whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def remove_navigation_garbage(text: str) -> str:
    """Удаляет типичный DW-мусор."""
    lowered = text.lower()
    for phrase in NAVIGATION_PHRASES:
        if phrase in lowered:
            lowered = lowered.replace(phrase, "")
    return lowered.strip()


def clean_article(text: str) -> str:
    """Полная очистка для пайплайна."""
    if not text:
        return ""

    text = clean_html(text)
    text = remove_navigation_garbage(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
