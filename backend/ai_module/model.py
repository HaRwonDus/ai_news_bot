import json
import re
from difflib import SequenceMatcher


_summarizer = None
_translator_de_en = None
_translator_de_ru = None


def _load_pipeline(task: str, model: str, **kwargs):
    """Load HuggingFace pipelines lazily so basic bot commands start fast."""
    try:
        from transformers import pipeline
    except Exception as exc:
        raise RuntimeError(
            "ML backend is not available. Install torch or use the CPU/CUDA bot image."
        ) from exc

    try:
        return pipeline(task, model=model, **kwargs)
    except Exception as exc:
        raise RuntimeError(f"Failed to load HuggingFace model '{model}': {exc}") from exc


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        _summarizer = _load_pipeline(
            "summarization",
            model="sshleifer/distilbart-cnn-12-6",
        )
    return _summarizer


def get_translator_de_en():
    global _translator_de_en
    if _translator_de_en is None:
        _translator_de_en = _load_pipeline(
            "translation",
            model="Helsinki-NLP/opus-mt-de-en",
        )
    return _translator_de_en


def get_translator_de_ru():
    global _translator_de_ru
    if _translator_de_ru is None:
        _translator_de_ru = _load_pipeline(
            "translation",
            model="facebook/nllb-200-distilled-600M",
            src_lang="deu_Latn",
            tgt_lang="rus_Cyrl",
        )
    return _translator_de_ru


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def is_similar(a: str, b: str, threshold: float = 0.75) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > threshold


def _format_news_item(item: dict, prefix: str = "🗞️") -> str:
    title = clean_text(item.get("title", ""))
    url = clean_text(item.get("url", ""))
    if title and url:
        return f"{prefix} {title}\n🔗 {url}"
    if title:
        return f"{prefix} {title}"
    return ""


def _short_excerpt(text: str, max_chars: int = 420) -> str:
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def summarize_text_safe(
    text: str,
    max_chars: int = 1800,
    max_len: int = 80,
    min_len: int = 25,
):
    text = clean_text(text)
    if len(text) > max_chars:
        text = text[:max_chars]

    if len(text.split()) < 30:
        return None

    try:
        out = get_summarizer()(
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


def summarize_news(news_json: str):
    """Short /news digest. Falls back to titles when local ML is unavailable."""
    data = json.loads(news_json)
    summaries = []

    for item in data[:5]:
        title = clean_text(item.get("title", ""))
        if not title:
            continue

        try:
            summary = get_summarizer()(
                title,
                max_length=50,
                min_length=10,
                do_sample=False,
            )[0]["summary_text"]
            summaries.append(f"🗞️ {summary}\n🔗 {item.get('url', '')}")
        except Exception:
            formatted = _format_news_item(item)
            if formatted:
                summaries.append(formatted)

    if not summaries:
        return "⚠️ Не удалось получить свежие новости."
    return "\n\n".join(summaries)


def smart_summarize(news_json: str):
    """Detailed /smartnews digest with graceful fallback for short articles."""
    data = json.loads(news_json)
    summaries = []
    seen_titles = []

    for item in data[:5]:
        title = clean_text(item.get("title", ""))
        if not title or any(is_similar(title, seen) for seen in seen_titles):
            continue
        seen_titles.append(title)

        content = clean_text(item.get("content", ""))
        summary = summarize_text_safe(content) if content else None

        if summary:
            summaries.append(f"📰 *{title}*\n{summary}\n🔗 {item.get('url', '')}")
            continue

        excerpt = _short_excerpt(content)
        fallback = _format_news_item(item, prefix="📰")
        if excerpt:
            fallback = f"{fallback}\n\n{excerpt}"
        if fallback:
            summaries.append(fallback)

    if not summaries:
        return "⚠️ Не удалось получить свежие новости для анализа."
    return "\n\n".join(summaries)


def summarize_multilang(news_json: str):
    """Create a DE/EN/RU digest when translation models are available."""
    data = json.loads(news_json)
    results = []

    for item in data[:5]:
        content = clean_text(item.get("content", ""))
        if len(content) < 300:
            continue

        summary_de = summarize_text_safe(content)
        if not summary_de:
            fallback = _format_news_item(item, prefix="📰")
            if fallback:
                results.append(fallback)
            continue

        try:
            summary_en = get_translator_de_en()(summary_de)[0]["translation_text"]
            summary_ru = get_translator_de_ru()(summary_de)[0]["translation_text"]
            results.append(
                f"📰 *{item['title']}*\n\n"
                f"🇩🇪 **DE:** {summary_de}\n\n"
                f"🇬🇧 **EN:** {summary_en}\n\n"
                f"🇷🇺 **RU:** {summary_ru}\n\n"
                f"🔗 {item['url']}"
            )
        except Exception:
            fallback = _format_news_item(item, prefix="📰")
            if fallback:
                results.append(fallback)

    if not results:
        return "⚠️ Нет подходящих новостей для перевода."
    return "\n\n".join(results)
