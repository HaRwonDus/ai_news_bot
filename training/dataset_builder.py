from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path


CATEGORIES = ["AI", "Robotics", "Research", "Business", "Security", "Open Source"]
DATA_ROOT = Path("data")
VERSIONS_DIR = DATA_ROOT / "versions"
PROCESSED_DIR = DATA_ROOT / "processed"
RAW_DIR = DATA_ROOT / "raw"


BASE_EXAMPLES: dict[str, list[str]] = {
    "AI": [
        "OpenAI releases a compact reasoning model for enterprise assistants",
        "AI chip demand grows as companies deploy generative copilots",
        "A new benchmark compares language models on planning tasks",
        "Researchers improve retrieval augmented generation for news summaries",
        "Multimodal AI systems learn to explain charts and images",
        "A startup launches an agent platform for automated workflows",
    ],
    "Robotics": [
        "Warehouse robots learn safer navigation around human workers",
        "Humanoid robot maker reports progress in hand manipulation",
        "Autonomous drones inspect bridges after severe storms",
        "A factory adds collaborative robots to the assembly line",
        "Robotics researchers demonstrate better reinforcement learning control",
        "Delivery robots expand trials on university campuses",
    ],
    "Research": [
        "Scientists publish a paper on efficient transformer training",
        "A university lab releases findings on synthetic data quality",
        "Peer reviewers debate reproducibility in machine learning papers",
        "New research explores causal inference for recommendation systems",
        "A conference highlights progress in privacy preserving analytics",
        "Researchers compare evaluation methods for open domain assistants",
    ],
    "Business": [
        "Cloud revenue rises as enterprises increase AI infrastructure spending",
        "A software company acquires a data automation startup",
        "Investors back a new platform for corporate knowledge search",
        "Tech stocks move higher after strong quarterly earnings",
        "Consulting firms expand services around generative AI adoption",
        "A chip manufacturer signs a multi year supply agreement",
    ],
    "Security": [
        "Security teams patch a critical vulnerability in a popular library",
        "Researchers uncover a phishing campaign targeting developer accounts",
        "A cloud provider adds stronger identity controls for administrators",
        "Ransomware activity increases against regional service providers",
        "A report warns that prompt injection can expose private documents",
        "Cybersecurity startup launches monitoring for AI application risks",
    ],
    "Open Source": [
        "Maintainers release a new version of an open source vector database",
        "A community project adds support for faster model inference",
        "Developers debate governance for a widely used Python package",
        "An open source framework improves tools for local LLM deployment",
        "Contributors publish a roadmap for a Kubernetes operator",
        "A foundation announces funding for critical open source maintainers",
    ],
}


@dataclass(frozen=True)
class DatasetSpec:
    version: str
    repeat: int
    noisy_labels: int
    label_prefix: bool = True
    extra_examples: tuple[tuple[str, str], ...] = ()


SPECS = {
    "v1": DatasetSpec(version="v1", repeat=2, noisy_labels=0),
    "v2": DatasetSpec(
        version="v2",
        repeat=1,
        noisy_labels=6,
        label_prefix=False,
        extra_examples=(
            ("AI", "A business team says every product is now powered by AI"),
            ("Business", "Security budgets rise after several AI related incidents"),
            ("Security", "Open source maintainers discuss secure release signing"),
            ("Open Source", "Researchers open source a robotics simulation toolkit"),
        ),
    ),
    "v3": DatasetSpec(
        version="v3",
        repeat=3,
        noisy_labels=3,
        extra_examples=(
            ("AI", "Model registry workflows help teams compare AI experiments"),
            ("Robotics", "Robot perception systems improve with synthetic datasets"),
            ("Research", "A benchmark tracks accuracy precision recall and f1"),
            ("Business", "Enterprises measure return on investment from automation"),
            ("Security", "Security analysts monitor drift in production classifiers"),
            ("Open Source", "Open source contributors publish reproducible ML pipelines"),
        ),
    ),
}


def _rows_for_spec(spec: DatasetSpec) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for _ in range(spec.repeat):
        for label, examples in BASE_EXAMPLES.items():
            for text in examples:
                rows.append({"text": _format_text(label, text, spec.label_prefix), "label": label})

    for label, text in spec.extra_examples:
        rows.append({"text": _format_text(label, text, spec.label_prefix), "label": label})

    if spec.noisy_labels:
        labels = CATEGORIES[:]
        changed = 0
        per_label_budget = max(1, spec.noisy_labels // len(labels))
        for label in labels:
            label_rows = [idx for idx, row in enumerate(rows) if row["label"] == label]
            for idx in label_rows[:per_label_budget]:
                if changed >= spec.noisy_labels:
                    break
                rows[idx]["label"] = labels[(labels.index(label) + 2) % len(labels)]
                changed += 1
            if changed >= spec.noisy_labels:
                break

    return rows


def _format_text(label: str, text: str, label_prefix: bool) -> str:
    if label_prefix:
        return f"{label} news: {text}"
    return text


def build_dataset(version: str) -> Path:
    if version not in SPECS:
        raise ValueError(f"Unknown dataset version: {version}. Available: {', '.join(SPECS)}")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)

    spec = SPECS[version]
    rows = _rows_for_spec(spec)
    output_path = VERSIONS_DIR / f"dataset_{version}.csv"
    raw_path = RAW_DIR / f"seed_{version}.jsonl"
    metadata_path = PROCESSED_DIR / f"dataset_{version}_metadata.json"

    with raw_path.open("w", encoding="utf-8") as raw_file:
        for row in rows:
            raw_file.write(json.dumps(row, ensure_ascii=True) + "\n")

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "dataset_version": version,
        "rows": len(rows),
        "labels": CATEGORIES,
        "source": str(raw_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output_path


def ensure_dataset(version: str) -> Path:
    return build_dataset(version)


def build_all() -> list[Path]:
    return [build_dataset(version) for version in SPECS]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build versioned news classification datasets.")
    parser.add_argument("--version", choices=sorted(SPECS), help="Build only one dataset version.")
    args = parser.parse_args()

    paths = [build_dataset(args.version)] if args.version else build_all()
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
