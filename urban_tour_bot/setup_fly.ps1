<#
Automates local Fly + GitHub Secrets setup for this repository.

Usage:
  1. Open PowerShell in the repository root.
  2. Run: .\urban_tour_bot\setup_fly.ps1

The script will:
  - Ensure `flyctl` and `gh` are installed
  - Run `flyctl auth login` (you complete login in the browser)
  - Optionally create a Fly app
  - Set Fly secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) using `flyctl secrets set`
  - Store `FLY_API_TOKEN`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in GitHub Actions Secrets for this repo

Security: you enter secrets locally; the script will not send them over chat.
#>

Set-StrictMode -Version Latest

function Fail($msg){ Write-Error $msg; exit 1 }

if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)){
    Fail "flyctl not found. Install it first: https://github.com/superfly/flyctl/releases/latest"
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)){
    Fail "GitHub CLI (gh) not found. Install it (https://cli.github.com/) and authenticate via 'gh auth login'"
}

Write-Host "1) Logging in to Fly (browser will open). Please complete login."
flyctl auth login

Write-Host "Retrieving Fly API token..."
$flyToken = & flyctl auth token 2>&1
if ($LASTEXITCODE -ne 0){
    Write-Warning "Couldn't retrieve Fly token with 'flyctl auth token'. You can create a token at https://fly.io/user/personal_access_tokens and set it manually in GitHub secrets."
    $flyToken = Read-Host "Paste Fly API token (or leave empty to skip setting it in GitHub)"
}

$appName = Read-Host "Enter Fly app name to create (or press Enter to skip)"
if ($appName -ne ""){
    try{
        flyctl apps show $appName > $null 2>&1
        if ($LASTEXITCODE -ne 0){
            Write-Host "Creating Fly app: $appName"
            flyctl apps create $appName --region ams
        } else {
            Write-Host "Fly app $appName already exists or is accessible."
        }
    } catch {
        Write-Warning "App create/show returned error: $_"
    }
}

Write-Host "Now provide your Telegram bot secrets (they will be used for Fly secrets and GitHub Actions Secrets)."
$teleTokenSecure = Read-Host "TELEGRAM_BOT_TOKEN (input hidden)" -AsSecureString
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($null) > $null 2>&1
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($teleTokenSecure)
$teleToken = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) > $null 2>&1

$chatId = Read-Host "TELEGRAM_CHAT_ID (e.g. 123456789)"

if ($teleToken -and $chatId){
    Write-Host "Setting Fly secrets (requires app context)..."
    try{
        if ($appName -ne ""){
            flyctl secrets set TELEGRAM_BOT_TOKEN=$teleToken TELEGRAM_CHAT_ID=$chatId -a $appName
        } else {
            flyctl secrets set TELEGRAM_BOT_TOKEN=$teleToken TELEGRAM_CHAT_ID=$chatId
        }
    } catch {
        Write-Warning "Failed to set Fly secrets: $_"
    }
}

Write-Host "Preparing to store secrets in GitHub Actions Secrets for this repository. Ensure you have run 'gh auth login' and are in the repository root."

$repo = ""
try{
    $repo = gh repo view --json nameWithOwner -q .nameWithOwner
} catch {
    Fail "Cannot determine GitHub repository via 'gh'. Run this script from a cloned repo and authenticate 'gh auth login' first."
}

if ($flyToken){
    Write-Host "Setting GitHub secret FLY_API_TOKEN..."
    gh secret set FLY_API_TOKEN --body "$flyToken"
}

Write-Host "Setting GitHub secret TELEGRAM_BOT_TOKEN..."
gh secret set TELEGRAM_BOT_TOKEN --body "$teleToken"
Write-Host "Setting GitHub secret TELEGRAM_CHAT_ID..."
gh secret set TELEGRAM_CHAT_ID --body "$chatId"

Write-Host "All done. Push to 'main' to trigger GitHub Actions deploy workflow (fly-deploy.yml)."
Write-Host "Reminder: do NOT paste secrets into chat."
