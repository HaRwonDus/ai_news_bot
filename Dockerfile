FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.4.1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        libssl-dev \
        patchelf \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal \
    && rustup default stable

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
RUN poetry install --no-interaction --no-ansi

COPY backend ./backend

RUN poetry run maturin build --manifest-path backend/rust_core/Cargo.toml --release --out dist \
    && pip install --no-cache-dir dist/*.whl

CMD ["python", "-m", "backend.main"]
