import os
import time
from threading import Lock
from typing import Any


_run = None
_lock = Lock()
_warned = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def wandb_enabled() -> bool:
    return _env_bool("WANDB_ENABLED", default=False)


def init_wandb(config: dict[str, Any] | None = None):
    """Initialize W&B lazily and keep the app usable when W&B is not configured."""
    global _run, _warned

    if not wandb_enabled():
        return None

    with _lock:
        if _run is not None:
            return _run

        try:
            import wandb

            init_kwargs: dict[str, Any] = {
                "project": os.getenv("WANDB_PROJECT", "ai-news-bot"),
                "name": os.getenv("WANDB_RUN_NAME") or None,
                "entity": os.getenv("WANDB_ENTITY") or None,
                "mode": os.getenv("WANDB_MODE") or "online",
                "config": config or {},
            }
            init_kwargs = {key: value for key, value in init_kwargs.items() if value is not None}
            _run = wandb.init(**init_kwargs)
            return _run
        except Exception as exc:
            if not _warned:
                print(f"W&B disabled: {exc}")
                _warned = True
            return None


def log_metrics(metrics: dict[str, Any], step: int | None = None) -> None:
    run = init_wandb()
    if run is None:
        return

    try:
        import wandb

        payload = {"timestamp": time.time(), **metrics}
        wandb.log(payload, step=step)
    except Exception as exc:
        print(f"W&B log skipped: {exc}")


def log_event(event: str, metrics: dict[str, Any] | None = None) -> None:
    payload = {"event": event}
    if metrics:
        payload.update(metrics)
    log_metrics(payload)


def finish_wandb() -> None:
    global _run

    if _run is None:
        return

    try:
        _run.finish()
    finally:
        _run = None
