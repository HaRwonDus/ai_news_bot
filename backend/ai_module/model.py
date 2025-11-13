import json
import re
from transformers import pipeline
from difflib import SequenceMatcher
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from backend.db.database import Base

# --- 🔧 Инициализация моделей ---
# Суммаризация немецких новостей
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Переводчики
translator_de_en = pipeline("translation", model="Helsinki-NLP/opus-mt-de-en")
translator_de_ru = pipeline(
    "translation",
    model="facebook/nllb-200-distilled-600M",
    src_lang="deu_Latn",
    tgt_lang="rus_Cyrl",
)

# --- 🔹 Вспомогательные функции ---
def clean_text(text: str) -> str:
    """Очистка текста от мусора и лишних пробелов"""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_similar(a, b, threshold=0.75):
    """Проверка похожести строк (для фильтрации дублей)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def summarize_text_safe(
    text: str,
    max_chars: int = 1800,
    max_len: int = 80,
    min_len: int = 25,
):
    """
    Безопасная обёртка над summarizer:
    - обрезает длинные тексты
    - игнорирует слишком короткие
    - защищает от ошибок huggingface
    """
    text = clean_text(text)
    if len(text) > max_chars:
        text = text[:max_chars]

    if len(text.split()) < 30:  # меньше ~30 слов — слишком коротко
        return None

    try:
        out = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False,
            truncation=True,
        )
        if not out or "summary_text" not in out[0]:
            return None
        return out[0]["summary_text"]
    except Exception:
        return None


# --- 🔹 Короткий дайджест (/news) ---
def summarize_news(news_json: str):
    """Краткая сводка по заголовкам (для команды /news)"""
    data = json.loads(news_json)
    summaries = []

    for n in data[:5]:
        title = n.get("title", "").strip()
        if not title:
            continue

        try:
            summary = summarizer(
                title, max_length=50, min_length=10, do_sample=False
            )[0]["summary_text"]
            summaries.append(f"🗞️ {summary}\n🔗 {n.get('url', '')}")
        except Exception as e:
            summaries.append(f"⚠️ Ошибка при суммаризации: {e}\n{title}")

    if not summaries:
        return "⚠️ Нет подходящих новостей для отображения."
    return "\n\n".join(summaries)


# --- 🔹 Глубокая выжимка (/smartnews) ---
def smart_summarize(news_json: str):
    """Создаёт расширенный дайджест из текста статей"""
    data = json.loads(news_json)
    clean_articles = []
    seen_titles = []

    for item in data:
        title = clean_text(item["title"])
        if any(is_similar(title, t) for t in seen_titles):
            continue
        seen_titles.append(title)

        content = clean_text(item.get("content", ""))
        if len(content) > 300:  # игнорируем пустые и короткие тексты
            clean_articles.append({
                "title": title,
                "url": item["url"],
                "content": content
            })

    summaries = []

    for art in clean_articles[:5]:
        summary = summarize_text_safe(art["content"])
        if not summary:
            summaries.append(
                f"⚠️ Пропущено: текст слишком короткий или не подошёл для суммаризации.\n{art['title']}"
            )
            continue

        summaries.append(f"📰 *{art['title']}*\n{summary}\n🔗 {art['url']}")

    if not summaries:
        return "⚠️ Не удалось создать выжимку. Возможно, мало текста."
    return "\n\n".join(summaries)


# --- 🔹 Мультиязычная версия (/multilangnews) ---
def summarize_multilang(news_json: str):
    """Создаёт выжимку на 3 языках (DE, EN, RU)"""
    data = json.loads(news_json)
    results = []

    for n in data[:5]:
        content = clean_text(n["content"])
        if len(content) < 300:
            continue

        summary_de = summarize_text_safe(content)
        if not summary_de:
            continue

        try:
            summary_en = translator_de_en(summary_de)[0]["translation_text"]
            summary_ru = translator_de_ru(summary_de)[0]["translation_text"]

            block = (
                f"📰 *{n['title']}*\n\n"
                f"🇩🇪 **DE:** {summary_de}\n\n"
                f"🇬🇧 **EN:** {summary_en}\n\n"
                f"🇷🇺 **RU:** {summary_ru}\n\n"
                f"🔗 {n['url']}"
            )
            results.append(block)
        except Exception as e:
            results.append(f"⚠️ Ошибка при обработке статьи: {e}")

    if not results:
        return "⚠️ Нет подходящих новостей для перевода."
    return "\n\n".join(results)

