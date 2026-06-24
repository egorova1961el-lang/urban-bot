$ErrorActionPreference = 'Stop'
$envFile = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Definition) '.env'
if (-not (Test-Path $envFile)) { Write-Error "Env file not found: $envFile"; exit 1 }
$lines = Get-Content $envFile
$bot = ($lines | Select-String '^TELEGRAM_BOT_TOKEN=').ToString().Split('=',2)[1].Trim()
$chat = ($lines | Select-String '^TELEGRAM_CHAT_ID=').ToString().Split('=',2)[1].Trim()
$fly = Join-Path $env:USERPROFILE 'Downloads\flyctl_0.4.60_Windows_x86_64\flyctl.exe'
if (-not (Test-Path $fly)) { $fly = 'flyctl' }
Write-Host "Using flyctl: $fly"
$appName = 'urban-bot'
try {
    & $fly apps show $appName > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating Fly app: $appName"
        & $fly apps create $appName
    } else {
        Write-Host "Fly app $appName already exists"
    }
} catch {
    Write-Warning "apps show/create returned: $_"
}
try {
    Write-Host "Setting Fly secrets for app $appName (values hidden)"
    & $fly secrets set TELEGRAM_BOT_TOKEN=$bot TELEGRAM_CHAT_ID=$chat -a $appName
    Write-Host "Fly secrets set."
} catch {
    Write-Warning "Failed to set Fly secrets: $_"
    exit 1
}
