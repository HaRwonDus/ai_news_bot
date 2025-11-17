from transformers import pipeline

# Немецкий sentiment-анализ (очень точный)
sentiment_model = pipeline(
    "sentiment-analysis",
    model="oliverguhr/german-sentiment-bert"
)

def detect_sentiment(text: str) -> str:
    """
    Возвращает: positive / negative / neutral
    """
    try:
        result = sentiment_model(text[:500])[0]  # ограничим текст
        label = result["label"].lower()

        if "positive" in label:
            return "positive"
        if "negative" in label:
            return "negative"
        return "neutral"

    except Exception:
        return "neutral"
