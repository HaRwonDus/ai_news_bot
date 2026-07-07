from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    accuracy_score,
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
)


def evaluate_predictions(y_test, predictions, labels: list[str], output_dir: Path) -> dict[str, float | str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )
    accuracy = accuracy_score(y_test, predictions)

    matrix = confusion_matrix(y_test, predictions, labels=labels)
    display = ConfusionMatrixDisplay(confusion_matrix=matrix, display_labels=labels)
    fig, ax = plt.subplots(figsize=(9, 7))
    display.plot(ax=ax, cmap="Blues", xticks_rotation=30, colorbar=False)
    fig.tight_layout()
    confusion_path = output_dir / "confusion_matrix.png"
    fig.savefig(confusion_path, dpi=150)
    plt.close(fig)

    report = classification_report(y_test, predictions, labels=labels, zero_division=0)
    report_path = output_dir / "classification_report.txt"
    report_path.write_text(report, encoding="utf-8")

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "confusion_matrix_path": str(confusion_path),
        "classification_report_path": str(report_path),
    }


def evaluate_classifier(model, x_test, y_test, labels: list[str], output_dir: Path) -> dict[str, float | str]:
    predictions = model.predict(x_test)
    return evaluate_predictions(y_test, predictions, labels, output_dir)
