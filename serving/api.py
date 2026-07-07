from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter as PromCounter
from prometheus_client import Gauge, Histogram, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from pydantic import BaseModel, Field
from starlette.responses import Response

from monitoring.drift_detector import DriftDetector
from serving.model_loader import RegistryModelLoader


app = FastAPI(title="AI News Classifier Serving", version="0.1.0")
loader = RegistryModelLoader()
recent_predictions: deque[str] = deque(maxlen=500)
recent_confidences: deque[float] = deque(maxlen=500)
drift_detector = DriftDetector()

prediction_count = PromCounter("prediction_count", "Number of predictions.", ["category"])
prediction_latency = Histogram("prediction_latency_seconds", "Prediction latency in seconds.")
prediction_errors = PromCounter("prediction_error_count", "Number of prediction errors.")
prediction_confidence = Histogram(
    "prediction_confidence",
    "Model confidence distribution.",
    buckets=(0.0, 0.25, 0.5, 0.7, 0.85, 0.95, 1.0),
)
category_share = Gauge("prediction_category_share", "Recent category share.", ["category"])
drift_detected = Gauge("data_drift_detected", "1 when category distribution drift is detected.")


class PredictionRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = ""


class PredictionResponse(BaseModel):
    category: str
    confidence: float
    model_uri: str


def _predict_with_confidence(model: Any, text: str) -> tuple[str, float]:
    category = str(model.predict([text])[0])
    classifier = model.named_steps.get("classifier") if hasattr(model, "named_steps") else None
    if classifier is not None and hasattr(model, "predict_proba"):
        probabilities = model.predict_proba([text])[0]
        confidence = float(np.max(probabilities))
    else:
        confidence = 1.0
    return category, confidence


def _update_distribution_metrics() -> None:
    total = len(recent_predictions)
    if total == 0:
        return
    counts = Counter(recent_predictions)
    for category, count in counts.items():
        category_share.labels(category=category).set(count / total)

    result = drift_detector.detect(counts, total)
    drift_detected.set(1 if result["drift_detected"] else 0)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model_uri": loader.model_uri}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    text = f"{payload.title}\n{payload.content}".strip()
    started = time.perf_counter()
    try:
        model = loader.get_model()
        category, confidence = _predict_with_confidence(model, text)
        prediction_count.labels(category=category).inc()
        prediction_confidence.observe(confidence)
        recent_predictions.append(category)
        recent_confidences.append(confidence)
        _update_distribution_metrics()
        return PredictionResponse(category=category, confidence=confidence, model_uri=loader.model_uri)
    except Exception as exc:
        prediction_errors.inc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        prediction_latency.observe(time.perf_counter() - started)


@app.post("/reload")
def reload_model() -> dict[str, str]:
    try:
        uri = loader.reload()
        return {"status": "reloaded", "model_uri": uri}
    except Exception as exc:
        prediction_errors.inc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/monitoring/drift")
def drift() -> dict[str, object]:
    counts = Counter(recent_predictions)
    return drift_detector.detect(counts, len(recent_predictions))


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
