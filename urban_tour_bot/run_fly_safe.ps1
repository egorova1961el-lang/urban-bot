$flyPath = 'C:\Users\Лиза\Downloads\flyctl_0.4.60_Windows_x86_64\flyctl.exe'
if (-not (Test-Path $flyPath)) { $flyPath = 'flyctl' }
$out = Join-Path $PSScriptRoot 'fly_safe_output.txt'
"Run started: $(Get-Date -Format o)" | Out-File $out -Encoding utf8
function RunCmd($args){
    try{
        $text = & $flyPath $args 2>&1 | Out-String
        "--- fly $args ---" | Out-File $out -Append -Encoding utf8
        $text | Out-File $out -Append -Encoding utf8
    } catch {
        "--- fly $args failed ---" | Out-File $out -Append -Encoding utf8
        "$_" | Out-File $out -Append -Encoding utf8
    }
}
RunCmd 'version'
RunCmd 'auth whoami'
RunCmd 'apps list'
RunCmd 'apps show urban-bot'
RunCmd 'secrets list -a urban-bot'
"Run finished: $(Get-Date -Format o)" | Out-File $out -Append -Encoding utf8
