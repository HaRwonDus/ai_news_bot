$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    throw ".env not found. Create it from .env.example and set BOT_TOKEN."
}

$tokenLine = Get-Content ".env" | Where-Object { $_ -match "^BOT_TOKEN=.+" } | Select-Object -First 1
if (-not $tokenLine -or $tokenLine -match "telegram_bot_token") {
    throw "BOT_TOKEN is missing or still a placeholder in .env."
}

docker compose --profile bot up -d bot
docker compose ps bot
