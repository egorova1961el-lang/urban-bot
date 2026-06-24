param(
    [string]$Repo = 'egorova1961el-lang/urban-bot'
)

try{
    $repoRoot = Convert-Path .
    $envFile = Join-Path $repoRoot 'urban_tour_bot\.env'
    if (-not (Test-Path $envFile)){
        Write-Error "Env file not found: $envFile"; exit 1
    }

    $lines = Get-Content $envFile
    $botLine = $lines | Select-String '^TELEGRAM_BOT_TOKEN=' | Select-Object -First 1
    $chatLine = $lines | Select-String '^TELEGRAM_CHAT_ID=' | Select-Object -First 1
    if (-not $botLine -or -not $chatLine){ Write-Error 'Required keys missing in .env'; exit 1 }
    $bot = $botLine.ToString().Split('=',2)[1].Trim()
    $chat = $chatLine.ToString().Split('=',2)[1].Trim()

        $gh = 'C:\Program Files\GitHub CLI\gh.exe'
        $fly = Join-Path $env:USERPROFILE 'Downloads\flyctl_0.4.60_Windows_x86_64\flyctl.exe'

    if (-not (Test-Path $gh)){
        Write-Warning "gh not found at $gh; trying system PATH"
        $gh = 'gh'
    }
    if (-not (Test-Path $fly)){
        Write-Warning "flyctl not found at $fly; trying system PATH"
        $fly = 'flyctl'
    }

        Write-Host 'Setting GitHub Actions secrets for repo' $Repo
        & $gh secret set TELEGRAM_BOT_TOKEN --repo $Repo --body $bot
        & $gh secret set TELEGRAM_CHAT_ID --repo $Repo --body $chat

    Write-Host 'Attempting to set Fly secrets (app: urban-bot)...'
    try{
        & $fly secrets set TELEGRAM_BOT_TOKEN=$bot TELEGRAM_CHAT_ID=$chat -a urban-bot
    } catch {
        Write-Warning "Failed to set Fly secrets: $_"
    }
        $appName = 'urban-bot'
        Write-Host "Attempting to set Fly secrets (app: $appName)..."
        try{
            & $fly apps show $appName > $null 2>&1
            if ($LASTEXITCODE -ne 0){
                Write-Host "Creating Fly app: $appName"
                & $fly apps create $appName
            } else {
                Write-Host "Fly app $appName exists."
            }
            & $fly secrets set TELEGRAM_BOT_TOKEN=$bot TELEGRAM_CHAT_ID=$chat -a $appName
        } catch {
            Write-Warning "Failed to set Fly secrets: $_"
        }

    Write-Host 'Done.'
} catch {
    Write-Error "Error: $_"
    exit 1
}
