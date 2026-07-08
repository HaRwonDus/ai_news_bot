# Docker Quickstart

Use this file when you need to start the whole local MLOps demo on a new machine.

## Start Everything

From the project root:

```powershell
.\scripts\start_mlops.ps1
```

This does three things:

1. Starts `postgres`, `minio`, and `mlflow`.
2. Runs the 3-run sklearn demo training so `NewsClassifier` exists in MLflow Registry.
3. Starts `serving`, `prometheus`, and `grafana`.

If PostgreSQL does not become healthy, the script automatically falls back to MySQL and starts MLflow with a MySQL backend.

Open:

- MLflow: http://localhost:5000
- FastAPI: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Start Without Training

Use this only if a production model already exists in MLflow Registry:

```powershell
.\scripts\start_mlops.ps1 -SkipTraining
```

## Force A Database Backend

Default mode is automatic:

```powershell
.\scripts\start_mlops.ps1 -DbBackend auto
```

Force PostgreSQL:

```powershell
.\scripts\start_mlops.ps1 -DbBackend postgres
```

Force MySQL:

```powershell
.\scripts\start_mlops.ps1 -DbBackend mysql
```

MySQL and PostgreSQL use separate Docker volumes, so MLflow history is isolated per backend.

## Stop Everything

```powershell
.\scripts\stop_mlops.ps1
```

This stops containers but keeps Docker volumes. MLflow history, PostgreSQL data, and MinIO artifacts remain available for the next start.

## Telegram Bot

The MLOps stack can run without Telegram credentials. The bot needs `.env`.

Create `.env` from the template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the real token:

```env
BOT_TOKEN=123456:real_telegram_bot_token
WANDB_ENABLED=false
```

Start only the bot:

```powershell
.\scripts\start_bot.ps1
```

Or manually:

```powershell
docker compose --profile bot up -d bot
```

## PyTorch Training With CPU Fallback

This mode works on laptops and other CPU-only machines. It uses a CPU PyTorch image, so it does not require CUDA and does not reserve a GPU at Docker level.

```powershell
docker compose --profile torch run --rm training-torch
```

Logged MLflow params include:

- `trainer=torch`
- `requested_device=auto`
- `device=cpu` or `device=cuda`
- `cuda_available`
- `cuda_device_count`
- `gpu_name`
- `torch_version`

## Forced NVIDIA CUDA Training

Use this only on a machine with NVIDIA GPU support in Docker:

```powershell
docker compose --profile cuda run --rm training-cuda
```

This service uses the CUDA PyTorch image and requests GPU devices from Docker. On a laptop without NVIDIA GPU, it can fail before Python starts. Use `training-torch` on CPU-only machines.

## Manual Startup

If you do not want to use the script:

```powershell
docker compose up -d postgres minio mlflow
docker compose --profile tools run --rm training python -m training.train --demo-runs
docker compose up -d serving prometheus grafana
```

Manual MySQL startup:

```powershell
docker compose --profile mysql up -d mysql minio mlflow-mysql
docker compose --profile tools run --rm --no-deps training python -m training.train --demo-runs
docker compose up -d --no-deps serving prometheus grafana
```

Check services:

```powershell
docker compose ps
```
