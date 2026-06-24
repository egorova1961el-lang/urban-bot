# Wrapper: expose flyctl and gh in this session and run setup_fly.ps1
$fly = Join-Path $env:USERPROFILE 'Downloads\\flyctl_0.4.60_Windows_x86_64\\flyctl.exe'
$gh = 'C:\\Program Files\\GitHub CLI\\gh.exe'
function flyctl { & $fly @args }
function gh { & $gh @args }
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
. "$scriptDir\\setup_fly.ps1"
