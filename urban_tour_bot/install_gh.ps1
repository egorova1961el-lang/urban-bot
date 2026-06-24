$ErrorActionPreference = 'Stop'
Write-Host 'Fetching latest gh release info...'
$rel = Invoke-RestMethod -UseBasicParsing https://api.github.com/repos/cli/cli/releases/latest
$asset = $rel.assets | Where-Object { $_.name -like '*windows*amd64*.msi' } | Select-Object -First 1
if (-not $asset) { $asset = $rel.assets | Where-Object { $_.name -like '*windows*amd64*' } | Select-Object -First 1 }
if (-not $asset) { Write-Error 'Could not find a Windows amd64 asset on releases page.'; exit 1 }
$msi = Join-Path $env:TEMP $asset.name
Write-Host "Downloading $($asset.browser_download_url) to $msi"
Invoke-WebRequest $asset.browser_download_url -OutFile $msi
Write-Host 'Launching installer (UAC prompt will appear).'
Start-Process msiexec -ArgumentList '/i',$msi -Verb runAs -Wait
Write-Host 'Installation finished. Checking gh version:'
gh --version
