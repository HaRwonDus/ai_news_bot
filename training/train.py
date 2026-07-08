from __future__ import annotations

import argparse
import os
import time
import warnings
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature
from mlflow.tracking import MlflowClient
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

from training.dataset_builder import CATEGORIES, ensure_dataset
from training.evaluate import evaluate_classifier


EXPERIMENT_NAME = "ai-news-classifier"
MODEL_NAME = "NewsClassifier"
EMBEDDING_MODEL = "tfidf-word-ngram"


def _set_tracking_uri() -> None:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment(EXPERIMENT_NAME)


def _transition_stage(run_id: str, stage: str) -> str | None:
    if not stage:
        return None

    client = MlflowClient()
    versions = client.search_model_versions(f"run_id = '{run_id}'")
    if not versions:
        return None

    version = sorted(versions, key=lambda item: int(item.version))[-1]
    if stage == "Development":
        client.set_model_version_tag(MODEL_NAME, version.version, "demo_stage", "Development")
        return version.version

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, module="mlflow")
        client.transition_model_version_stage(
            name=MODEL_NAME,
            version=version.version,
            stage=stage,
            archive_existing_versions=(stage == "Production"),
        )
    client.set_model_version_tag(MODEL_NAME, version.version, "stage_reason", f"Demo transition to {stage}")
    return version.version


def _log_common_params(
    model_name: str,
    embedding_model: str,
    dataset_version: str,
    ngram_max: int,
    train_rows: int,
    test_rows: int,
    trainer: str,
) -> None:
    mlflow.log_param("model_name", model_name)
    mlflow.log_param("embedding_model", embedding_model)
    mlflow.log_param("dataset_version", dataset_version)
    mlflow.log_param("ngram_max", ngram_max)
    mlflow.log_param("train_rows", train_rows)
    mlflow.log_param("test_rows", test_rows)
    mlflow.log_param("trainer", trainer)


def train_sklearn_once(
    dataset_version: str,
    c_value: float,
    ngram_max: int,
    run_name: str | None = None,
    stage: str | None = None,
) -> dict[str, float | str | None]:
    _set_tracking_uri()
    dataset_path = ensure_dataset(dataset_version)
    data = pd.read_csv(dataset_path)

    x_train, x_test, y_train, y_test = train_test_split(
        data["text"],
        data["label"],
        test_size=0.35,
        random_state=42,
        stratify=data["label"],
    )

    model = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, ngram_max), lowercase=True)),
            ("classifier", LogisticRegression(C=c_value, max_iter=1000, class_weight="balanced")),
        ]
    )

    with mlflow.start_run(run_name=run_name or f"{MODEL_NAME}-{dataset_version}") as run:
        started = time.perf_counter()
        model.fit(x_train, y_train)
        train_seconds = time.perf_counter() - started

        output_dir = Path("artifacts") / run.info.run_id
        metrics = evaluate_classifier(model, x_test, y_test, CATEGORIES, output_dir)
        model_path = output_dir / "model.pkl"
        joblib.dump(model, model_path)

        _log_common_params(
            model_name=MODEL_NAME,
            embedding_model=EMBEDDING_MODEL,
            dataset_version=dataset_version,
            ngram_max=ngram_max,
            train_rows=len(x_train),
            test_rows=len(x_test),
            trainer="sklearn",
        )
        mlflow.log_param("classifier_c", c_value)
        mlflow.log_param("device", "cpu")
        mlflow.log_param("cuda_available", False)
        mlflow.log_metric("train_seconds", train_seconds)
        mlflow.log_metrics(
            {
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
            }
        )
        mlflow.log_artifact(metrics["confusion_matrix_path"])
        mlflow.log_artifact(metrics["classification_report_path"])
        mlflow.log_artifact(str(model_path))
        mlflow.log_artifact(str(dataset_path), artifact_path="dataset")
        input_example = data["text"].head(2).tolist()
        signature = infer_signature(input_example, model.predict(input_example))
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
            input_example=input_example,
            signature=signature,
        )

        version = _transition_stage(run.info.run_id, stage or "")
        mlflow.set_tag("registry_stage", stage or "None")
        if version:
            mlflow.set_tag("model_version", version)

        result = {
            "run_id": run.info.run_id,
            "model_version": version,
            "stage": stage,
            "dataset_version": dataset_version,
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
        }
        print(result)
        return result


def train_torch_once(
    dataset_version: str,
    ngram_max: int,
    run_name: str | None = None,
    stage: str | None = None,
    device: str = "auto",
    epochs: int = 60,
    learning_rate: float = 0.03,
    batch_size: int = 16,
) -> dict[str, float | str | None]:
    _set_tracking_uri()
    dataset_path = ensure_dataset(dataset_version)
    data = pd.read_csv(dataset_path)

    with mlflow.start_run(run_name=run_name or f"{MODEL_NAME}-torch-{dataset_version}") as run:
        output_dir = Path("artifacts") / run.info.run_id
        from training.torch_trainer import train_torch_classifier

        metrics = train_torch_classifier(
            data=data,
            dataset_version=dataset_version,
            output_dir=output_dir,
            ngram_max=ngram_max,
            epochs=epochs,
            learning_rate=learning_rate,
            batch_size=batch_size,
            requested_device=device,
        )

        _log_common_params(
            model_name=f"{MODEL_NAME}Torch",
            embedding_model=EMBEDDING_MODEL,
            dataset_version=dataset_version,
            ngram_max=ngram_max,
            train_rows=int(metrics["train_rows"]),
            test_rows=int(metrics["test_rows"]),
            trainer="torch",
        )
        mlflow.log_param("requested_device", metrics["requested_device"])
        mlflow.log_param("device", metrics["device"])
        mlflow.log_param("cuda_available", metrics["cuda_available"])
        mlflow.log_param("cuda_device_count", metrics["cuda_device_count"])
        mlflow.log_param("gpu_name", metrics["gpu_name"])
        mlflow.log_param("torch_version", metrics["torch_version"])
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("learning_rate", learning_rate)
        mlflow.log_param("batch_size", batch_size)
        mlflow.log_metrics(
            {
                "accuracy": metrics["accuracy"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "train_seconds": metrics["train_seconds"],
                "final_train_loss": metrics["final_train_loss"],
                "max_cuda_memory_mb": metrics["max_cuda_memory_mb"],
            }
        )
        mlflow.log_artifact(metrics["confusion_matrix_path"])
        mlflow.log_artifact(metrics["classification_report_path"])
        mlflow.log_artifact(metrics["model_path"])
        mlflow.log_artifact(metrics["vectorizer_path"])
        mlflow.log_artifact(metrics["metadata_path"])
        mlflow.log_artifact(metrics["loss_path"])
        mlflow.log_artifact(str(dataset_path), artifact_path="dataset")
        mlflow.set_tag("registry_stage", stage or "None")
        mlflow.set_tag("cuda_training", str(metrics["device"] == "cuda").lower())

        result = {
            "run_id": run.info.run_id,
            "model_version": None,
            "stage": stage,
            "dataset_version": dataset_version,
            "device": metrics["device"],
            "gpu_name": metrics["gpu_name"],
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
        }
        print(result)
        return result


def run_demo() -> None:
    runs = [
        ("v1", 1.0, 1, "baseline-v1", "Production"),
        ("v2", 0.02, 1, "noisy-v2", "Staging"),
        ("v3", 3.0, 2, "expanded-v3", "Development"),
    ]
    results = [train_sklearn_once(*run) for run in runs]
    best = max(results, key=lambda item: float(item["f1"]))
    print(f"Best demo run by f1: {best}")
    print("Rollback demo: v2 stays in Staging, current Production remains the archived-best baseline unless you promote another version.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and register the AI news classifier.")
    parser.add_argument("--dataset-version", default="v1", choices=["v1", "v2", "v3"])
    parser.add_argument("--classifier-c", type=float, default=1.0)
    parser.add_argument("--ngram-max", type=int, default=1)
    parser.add_argument("--run-name")
    parser.add_argument("--stage", choices=["Development", "Staging", "Production"])
    parser.add_argument("--trainer", choices=["sklearn", "torch"], default="sklearn")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=0.03)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--demo-runs", action="store_true", help="Run v1/v2/v3 demo trainings.")
    args = parser.parse_args()

    if args.demo_runs:
        run_demo()
        return

    if args.trainer == "torch":
        train_torch_once(
            dataset_version=args.dataset_version,
            ngram_max=args.ngram_max,
            run_name=args.run_name,
            stage=args.stage,
            device=args.device,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            batch_size=args.batch_size,
        )
    else:
        train_sklearn_once(
            dataset_version=args.dataset_version,
            c_value=args.classifier_c,
            ngram_max=args.ngram_max,
            run_name=args.run_name,
            stage=args.stage,
        )


if __name__ == "__main__":
    main()
