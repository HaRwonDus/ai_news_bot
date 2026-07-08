from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from training.dataset_builder import CATEGORIES
from training.evaluate import evaluate_predictions


def _import_torch():
    try:
        import torch
        from torch import nn
    except ImportError as exc:
        raise RuntimeError(
            "PyTorch is not installed in this image. Use the training-torch or "
            "training-cuda service, or install torch before running --trainer torch."
        ) from exc
    return torch, nn


class _LinearNewsClassifier:
    def __init__(self, input_dim: int, output_dim: int):
        torch, nn = _import_torch()
        self.module = nn.Sequential(nn.Linear(input_dim, output_dim))
        self.torch = torch

    def to(self, device: str) -> None:
        self.module.to(device)


def _resolve_device(requested_device: str) -> dict[str, Any]:
    torch, _ = _import_torch()
    cuda_available = bool(torch.cuda.is_available())
    cuda_count = int(torch.cuda.device_count()) if cuda_available else 0

    if requested_device == "auto":
        resolved = "cuda" if cuda_available else "cpu"
    else:
        resolved = requested_device

    if resolved == "cuda" and not cuda_available:
        raise RuntimeError(
            "CUDA was requested, but torch.cuda.is_available() is False. "
            "Check NVIDIA drivers, Docker Desktop GPU support, and NVIDIA Container Toolkit."
        )

    gpu_name = torch.cuda.get_device_name(0) if resolved == "cuda" else ""
    return {
        "requested_device": requested_device,
        "device": resolved,
        "cuda_available": cuda_available,
        "cuda_device_count": cuda_count,
        "gpu_name": gpu_name,
        "torch_version": torch.__version__,
    }


def train_torch_classifier(
    data,
    dataset_version: str,
    output_dir: Path,
    ngram_max: int,
    epochs: int,
    learning_rate: float,
    batch_size: int,
    requested_device: str,
) -> dict[str, Any]:
    torch, nn = _import_torch()
    device_info = _resolve_device(requested_device)
    device = device_info["device"]

    x_train, x_test, y_train, y_test = train_test_split(
        data["text"],
        data["label"],
        test_size=0.35,
        random_state=42,
        stratify=data["label"],
    )

    vectorizer = TfidfVectorizer(
        ngram_range=(1, ngram_max),
        lowercase=True,
        max_features=2048,
    )
    x_train_matrix = vectorizer.fit_transform(x_train).astype(np.float32)
    x_test_matrix = vectorizer.transform(x_test).astype(np.float32)
    label_to_id = {label: idx for idx, label in enumerate(CATEGORIES)}
    id_to_label = {idx: label for label, idx in label_to_id.items()}

    y_train_ids = np.array([label_to_id[label] for label in y_train], dtype=np.int64)
    x_train_tensor = torch.from_numpy(x_train_matrix.toarray()).to(device)
    y_train_tensor = torch.from_numpy(y_train_ids).to(device)
    x_test_tensor = torch.from_numpy(x_test_matrix.toarray()).to(device)

    classifier = _LinearNewsClassifier(x_train_tensor.shape[1], len(CATEGORIES))
    classifier.to(device)
    model = classifier.module
    loss_fn = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    started = time.perf_counter()
    losses: list[float] = []
    for _ in range(epochs):
        permutation = torch.randperm(x_train_tensor.shape[0], device=device)
        epoch_losses: list[float] = []
        for start in range(0, x_train_tensor.shape[0], batch_size):
            indices = permutation[start : start + batch_size]
            logits = model(x_train_tensor[indices])
            loss = loss_fn(logits, y_train_tensor[indices])

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu().item()))
        losses.append(float(np.mean(epoch_losses)))

    train_seconds = time.perf_counter() - started
    model.eval()
    with torch.no_grad():
        logits = model(x_test_tensor)
        prediction_ids = torch.argmax(logits, dim=1).detach().cpu().numpy().tolist()

    predictions = [id_to_label[idx] for idx in prediction_ids]
    metrics = evaluate_predictions(y_test, predictions, CATEGORIES, output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "torch_model.pt"
    vectorizer_path = output_dir / "vectorizer.pkl"
    metadata_path = output_dir / "torch_metadata.json"
    loss_path = output_dir / "training_loss.json"

    torch.save(
        {
            "state_dict": model.state_dict(),
            "input_dim": x_train_tensor.shape[1],
            "labels": CATEGORIES,
            "dataset_version": dataset_version,
        },
        model_path,
    )
    joblib.dump(vectorizer, vectorizer_path)
    metadata = {
        **device_info,
        "trainer": "torch",
        "dataset_version": dataset_version,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "batch_size": batch_size,
        "ngram_max": ngram_max,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    loss_path.write_text(json.dumps({"loss": losses}, indent=2), encoding="utf-8")

    max_cuda_memory_mb = 0.0
    if device == "cuda":
        max_cuda_memory_mb = float(torch.cuda.max_memory_allocated() / 1024 / 1024)

    return {
        **metrics,
        **device_info,
        "trainer": "torch",
        "train_seconds": train_seconds,
        "final_train_loss": losses[-1],
        "max_cuda_memory_mb": max_cuda_memory_mb,
        "model_path": str(model_path),
        "vectorizer_path": str(vectorizer_path),
        "metadata_path": str(metadata_path),
        "loss_path": str(loss_path),
        "train_rows": len(x_train),
        "test_rows": len(x_test),
    }
