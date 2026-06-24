$ErrorActionPreference = 'Stop'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$envFile = Join-Path $scriptDir '.env'
if (-not (Test-Path $envFile)) {
    Write-Error "Env file not found: $envFile"
    exit 1
}
$lines = Get-Content $envFile
$bot = ($lines | Where-Object { $_ -match '^TELEGRAM_BOT_TOKEN=' }) -replace '^TELEGRAM_BOT_TOKEN=', ''
$chat = ($lines | Where-Object { $_ -match '^TELEGRAM_CHAT_ID=' }) -replace '^TELEGRAM_CHAT_ID=', ''
$bot = $bot.Trim()
$chat = $chat.Trim()
if ([string]::IsNullOrWhiteSpace($bot) -or [string]::IsNullOrWhiteSpace($chat)) {
    Write-Error 'TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing or empty in .env'
    exit 1
}
$fly = 'C:\Users\Лиза\Downloads\flyctl_0.4.60_Windows_x86_64\flyctl.exe'
if (-not (Test-Path $fly)) { $fly = 'flyctl' }
Write-Host "Using flyctl: $fly"
Write-Host 'Verifying Fly app urban-bot...'
& $fly apps show urban-bot
Write-Host 'Setting Fly secrets...'
& $fly secrets set "TELEGRAM_BOT_TOKEN=$bot" "TELEGRAM_CHAT_ID=$chat" -a urban-bot
Write-Host 'Fly secrets set successfully.'
