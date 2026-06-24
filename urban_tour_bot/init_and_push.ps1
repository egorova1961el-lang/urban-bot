<#
Initializes the repository, creates a GitHub repo, pushes to main, and sets GitHub Actions secrets.
Usage:
  1) Open PowerShell in the repository root.
  2) Run: .\urban_tour_bot\init_and_push.ps1

This script does NOT hardcode secrets. It reads Telegram values from .env if present,
asks for missing values, and stores them as GitHub Actions secrets.
#>

[CmdletBinding()]
param(
    [string]$RepoName = '',
    [switch]$Private,
    [switch]$UseFlyctl
)

Set-StrictMode -Version Latest

function Fail($message) {
    Write-Error $message
    exit 1
}

function CommandExists($name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Resolve-Path (Join-Path $scriptDir '..')
Set-Location $repoRoot

if (-not (CommandExists 'git')) {
    Fail 'git is not available. Please install Git and rerun this script.'
}
if (-not (CommandExists 'gh')) {
    Fail 'GitHub CLI (gh) is not available. Please install gh and rerun this script.'
}

Write-Host 'Repository root:' $repoRoot

# Initialize git if needed
if (-not (Test-Path (Join-Path $repoRoot '.git'))) {
    Write-Host 'Initializing git repository...'
    git init | Out-Null
    git branch -M main
} else {
    Write-Host 'Git repository already initialized.'
}

# Ensure .env is ignored
$gitignorePath = Join-Path $repoRoot '.gitignore'
if (Test-Path $gitignorePath) {
    $gitignore = Get-Content $gitignorePath -Raw
    if ($gitignore -notmatch '(^|\r?\n)\.env($|\r?\n)') {
        Add-Content -Path $gitignorePath -Value "`n.env"
        Write-Host 'Added .env to .gitignore.'
    }
}

# Stage files and commit if there are changes
$changes = git status --short
if ([string]::IsNullOrWhiteSpace($changes)) {
    Write-Host 'No changes to commit.'
} else {
    Write-Host 'Staging files...'
    git add .
    if (-not [string]::IsNullOrWhiteSpace(git status --short)) {
        git commit -m 'Initial commit: deploy Telegram bot to Fly'
        Write-Host 'Committed initial project state.'
    } else {
        Write-Host 'Nothing to commit after staging.'
    }
}

# Create or validate GitHub remote
$remoteOrigin = $null
try {
    $remoteOrigin = git remote get-url origin 2>$null
} catch {
    $remoteOrigin = $null
}

if ($remoteOrigin) {
    Write-Host 'Remote origin already set to:' $remoteOrigin
} else {
    if (-not $RepoName) {
        $RepoName = Read-Host 'Enter GitHub repository name (owner/repo or repo-name)'
    }
    if (-not $RepoName) {
        Fail 'GitHub repository name is required to create the remote.'
    }

    $createArgs = @('--source', '.', '--remote', 'origin', '--push')
    if ($Private) { $createArgs += '--private' } else { $createArgs += '--public' }
    $createArgs += $RepoName

    Write-Host 'Creating GitHub repo and pushing to remote...' 
    gh repo create @createArgs
    if ($LASTEXITCODE -ne 0) {
        Fail 'Failed to create GitHub repository. Verify your gh authentication and repo name.'
    }
}

# Push to GitHub
Write-Host 'Pushing branch main to origin...'
git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Fail 'Failed to push to GitHub. Check your remote and authentication.'
}
Write-Host 'Push complete.'

# Parse .env values
$envPath = Join-Path $repoRoot '.env'
$token = ''
$chatId = ''
$flyToken = ''

if (Test-Path $envPath) {
    $lines = Get-Content $envPath
    $token = ($lines | Where-Object { $_ -match '^TELEGRAM_BOT_TOKEN=' }) -replace '^TELEGRAM_BOT_TOKEN=', ''
    $chatId = ($lines | Where-Object { $_ -match '^TELEGRAM_CHAT_ID=' }) -replace '^TELEGRAM_CHAT_ID=', ''
    $flyToken = ($lines | Where-Object { $_ -match '^FLY_API_TOKEN=' }) -replace '^FLY_API_TOKEN=', ''
    $token = $token.Trim()
    $chatId = $chatId.Trim()
    $flyToken = $flyToken.Trim()
}

if (-not $token) {
    $token = Read-Host 'TELEGRAM_BOT_TOKEN not found in .env. Enter token now'
}
if (-not $chatId) {
    $chatId = Read-Host 'TELEGRAM_CHAT_ID not found in .env. Enter chat ID now'
}
if (-not $flyToken) {
    $flyToken = Read-Host 'FLY_API_TOKEN not found in .env. Paste it now (or leave empty to skip)'
}

if (-not $token -or -not $chatId) {
    Fail 'Telegram bot token and chat ID are required to set GitHub secrets.'
}

Write-Host 'Setting GitHub Actions secrets...'
gh secret set TELEGRAM_BOT_TOKEN --body $token
if ($LASTEXITCODE -ne 0) { Fail 'Failed to set TELEGRAM_BOT_TOKEN secret.' }
gh secret set TELEGRAM_CHAT_ID --body $chatId
if ($LASTEXITCODE -ne 0) { Fail 'Failed to set TELEGRAM_CHAT_ID secret.' }
Write-Host 'Telegram secrets written to GitHub.'

if ($flyToken) {
    gh secret set FLY_API_TOKEN --body $flyToken
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Failed to set FLY_API_TOKEN secret. Please set it manually in GitHub.' } else { Write-Host 'FLY_API_TOKEN written to GitHub.' }
} else {
    Write-Warning 'FLY_API_TOKEN was skipped. GitHub Actions deploy requires this secret to deploy to Fly.'
}

if ($UseFlyctl) {
    if (-not (CommandExists 'flyctl')) {
        Write-Warning 'flyctl not found. Skip Fly app creation and secret injection.'
    } else {
        $appName = Read-Host 'Enter Fly app name to create or update (default: urban-bot)'
        if (-not $appName) { $appName = 'urban-bot' }
        try {
            flyctl apps show $appName > $null 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Creating Fly app: $appName"
                flyctl apps create $appName
            } else {
                Write-Host "Fly app $appName already exists."
            }
            flyctl secrets set TELEGRAM_BOT_TOKEN=$token TELEGRAM_CHAT_ID=$chatId -a $appName
            Write-Host 'Fly app secrets set successfully.'
        } catch {
            Write-Warning "Failed to configure Fly app or secrets: $_"
        }
    }
}

Write-Host 'Setup complete.'
Write-Host 'Now your code is pushed and GitHub workflow is ready to deploy on push to main.'
Write-Host 'If FLY_API_TOKEN was not set, add it in GitHub repository secrets before deployment.'
