# AI News Bot MLOps Demo

This demo turns the bot into a local MLOps stand:

- MLflow Tracking and Model Registry
- PostgreSQL backend store
- MinIO artifact store
- versioned datasets
- FastAPI model serving from `models:/NewsClassifier/Production`
- Prometheus metrics
- Grafana dashboards
- simple data drift detection

## 1. Start MLflow

```powershell
docker compose up -d postgres minio mlflow
```

Open:

- MLflow UI: http://localhost:5000
- MinIO console: http://localhost:9001

Default local credentials:

- MinIO: `minioadmin` / `minioadmin`

## 2. Build Dataset Versions

The training script creates these automatically, but they can be generated manually:

```powershell
docker compose --profile tools run --rm training python -m training.dataset_builder
```

Generated layout:

```text
data/
  raw/
  processed/
  versions/
    dataset_v1.csv
    dataset_v2.csv
    dataset_v3.csv
```

## 3. Run Three Trainings

```powershell
docker compose --profile tools run --rm training python -m training.train --demo-runs
```

Each run logs:

- params: `model_name`, `embedding_model`, `dataset_version`, `classifier_c`, `ngram_max`
- metrics: `accuracy`, `precision`, `recall`, `f1`
- artifacts: `confusion_matrix.png`, `model.pkl`, `classification_report.txt`, dataset snapshot

Registry model:

- `NewsClassifier`
- v1: `Production`
- v2: `Staging`
- v3: tagged as `demo_stage=Development`

The demo keeps the noisy v2 away from Production, which shows the rollback story clearly.

## 3.1 CUDA Training

CUDA training is available as a separate PyTorch training service. It logs GPU-related params and metrics to MLflow:

- `trainer=torch`
- `requested_device=cuda`
- `device`
- `cuda_available`
- `cuda_device_count`
- `gpu_name`
- `torch_version`
- `max_cuda_memory_mb`
- `train_seconds`

Prerequisites:

- NVIDIA GPU and recent NVIDIA drivers
- Docker Desktop with GPU support enabled
- NVIDIA Container Toolkit available to Docker

Build and run:

```powershell
docker compose --profile cuda build training-cuda
docker compose --profile cuda run --rm training-cuda
```

For a non-GPU smoke test, use the normal MLflow image only if PyTorch is installed there, or run the CUDA image with CPU fallback:

```powershell
docker compose --profile cuda run --rm training-cuda python -m training.train `
  --trainer torch `
  --device auto `
  --dataset-version v3 `
  --run-name torch-auto-v3
```

If `--device cuda` is requested and CUDA is unavailable, training fails fast and explains what to check.

## 4. Serve The Production Model

```powershell
docker compose up -d serving
```

Predict:

```powershell
Invoke-RestMethod http://localhost:8000/predict `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"title":"Open source maintainers release a new model inference toolkit","content":""}'
```

The service loads:

```text
models:/NewsClassifier/Production
```

After changing the Production version in MLflow, call:

```powershell
Invoke-RestMethod http://localhost:8000/reload -Method Post
```

The service also reloads automatically every `MODEL_RELOAD_SECONDS`.

## 5. Prometheus And Grafana

```powershell
docker compose up -d prometheus grafana
```

Open:

- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Default Grafana credentials:

- `admin` / `admin`

Dashboard: `AI News Bot MLOps`

Metrics endpoint:

```text
http://localhost:8000/metrics
```

Tracked metrics:

- `prediction_count`
- `prediction_latency_seconds`
- `prediction_error_count`
- `prediction_confidence`
- `prediction_category_share`
- `data_drift_detected`

## 6. Drift Demo

Send many AI-like requests:

```powershell
1..30 | ForEach-Object {
  Invoke-RestMethod http://localhost:8000/predict `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"title":"AI model platform launches new reasoning assistant","content":"language model agents and neural networks"}'
}
```

Then inspect:

```powershell
Invoke-RestMethod http://localhost:8000/monitoring/drift
```

Expected alert text:

```text
Data Drift Detected
```
