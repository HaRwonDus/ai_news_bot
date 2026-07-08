_sentiment_model = None


def get_sentiment_model():
    global _sentiment_model
    if _sentiment_model is None:
        from transformers import pipeline

        _sentiment_model = pipeline(
            "sentiment-analysis",
            model="oliverguhr/german-sentiment-bert",
        )
    return _sentiment_model


def detect_sentiment(text: str) -> str:
    """Return positive, negative, or neutral."""
    try:
        result = get_sentiment_model()(text[:500])[0]
        label = result["label"].lower()

        if "positive" in label:
            return "positive"
        if "negative" in label:
            return "negative"
        return "neutral"
    except Exception:
        return "neutral"
