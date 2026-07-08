param(
    [switch]$SkipTraining,
    [switch]$TorchTraining,
    [switch]$CudaTraining,
    [ValidateSet("auto", "postgres", "mysql")]
    [string]$DbBackend = "auto",
    [int]$DbWaitSeconds = 90
)

$ErrorActionPreference = "Stop"

function Wait-ComposeServiceHealthy {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Service,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $cid = docker compose ps -q $Service
        if ($cid) {
            $health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $cid
            if ($health -eq "healthy" -or $health -eq "running") {
                return $true
            }
        }
        Start-Sleep -Seconds 3
    }

    return $false
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }

    return $false
}

function Start-PostgresStack {
    Write-Host "Starting MLflow stack with PostgreSQL..."
    try {
        docker compose up -d postgres minio mlflow
    } catch {
        Write-Warning "PostgreSQL stack failed to start: $($_.Exception.Message)"
        return $false
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "PostgreSQL stack command exited with code $LASTEXITCODE."
        return $false
    }

    $postgresHealthy = Wait-ComposeServiceHealthy -Service "postgres" -TimeoutSeconds $DbWaitSeconds
    if (-not $postgresHealthy) {
        return $false
    }

    return (Wait-HttpReady -Url "http://localhost:5000" -TimeoutSeconds $DbWaitSeconds)
}

function Start-MySqlStack {
    Write-Host "Starting MLflow stack with MySQL fallback..."
    try {
        docker compose --profile mysql up -d mysql minio mlflow-mysql
    } catch {
        Write-Warning "MySQL stack failed to start: $($_.Exception.Message)"
        return $false
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Warning "MySQL stack command exited with code $LASTEXITCODE."
        return $false
    }

    $mysqlHealthy = Wait-ComposeServiceHealthy -Service "mysql" -TimeoutSeconds $DbWaitSeconds
    if (-not $mysqlHealthy) {
        return $false
    }

    return (Wait-HttpReady -Url "http://localhost:5000" -TimeoutSeconds $DbWaitSeconds)
}

$usingMySql = $false

if ($DbBackend -eq "mysql") {
    $usingMySql = $true
    $ok = Start-MySqlStack
    if (-not $ok) {
        throw "MySQL did not become healthy within $DbWaitSeconds seconds."
    }
} elseif ($DbBackend -eq "postgres") {
    $ok = Start-PostgresStack
    if (-not $ok) {
        throw "PostgreSQL did not become healthy within $DbWaitSeconds seconds."
    }
} else {
    $ok = Start-PostgresStack
    if (-not $ok) {
        Write-Warning "PostgreSQL did not become healthy. Falling back to MySQL."
        docker compose stop mlflow postgres
        $usingMySql = $true
        $mysqlOk = Start-MySqlStack
        if (-not $mysqlOk) {
            throw "Neither PostgreSQL nor MySQL became healthy. Check Docker logs."
        }
    }
}

if (-not $SkipTraining) {
    Write-Host "Running sklearn demo training..."
    if ($usingMySql) {
        docker compose --profile tools run --rm --no-deps training python -m training.train --demo-runs
    } else {
        docker compose --profile tools run --rm training python -m training.train --demo-runs
    }
}

if ($TorchTraining) {
    Write-Host "Running PyTorch training with CPU-safe image..."
    if ($usingMySql) {
        docker compose --profile torch run --rm --no-deps training-torch
    } else {
        docker compose --profile torch run --rm training-torch
    }
}

if ($CudaTraining) {
    Write-Host "Running PyTorch training with NVIDIA GPU reservation..."
    if ($usingMySql) {
        docker compose --profile cuda run --rm --no-deps training-cuda
    } else {
        docker compose --profile cuda run --rm training-cuda
    }
}

Write-Host "Starting serving and monitoring..."
if ($usingMySql) {
    docker compose up -d --no-deps serving prometheus grafana
} else {
    docker compose up -d serving prometheus grafana
}

docker compose ps

if ($usingMySql) {
    $backend = "mysql"
} else {
    $backend = "postgres"
}

Write-Host ""
Write-Host "DB backend: $backend"
Write-Host "MLflow:     http://localhost:5000"
Write-Host "FastAPI:    http://localhost:8000"
Write-Host "Prometheus: http://localhost:9090"
Write-Host "Grafana:    http://localhost:3000"
