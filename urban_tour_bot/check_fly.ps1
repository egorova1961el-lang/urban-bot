$fly = Join-Path $env:USERPROFILE 'Downloads\flyctl_0.4.60_Windows_x86_64\flyctl.exe'
if (-not (Test-Path $fly)) { $fly = 'flyctl' }
$out = Join-Path $PSScriptRoot 'fly_status_output.txt'
"=== WHOAMI ===" | Out-File $out -Encoding utf8
try { & $fly auth whoami | Out-File $out -Append -Encoding utf8 } catch { "auth whoami failed: $_" | Out-File $out -Append -Encoding utf8 }
"=== APPS LIST ===" | Out-File $out -Append -Encoding utf8
try { & $fly apps list | Out-File $out -Append -Encoding utf8 } catch { "apps list failed: $_" | Out-File $out -Append -Encoding utf8 }
"=== APP SHOW urban-bot ===" | Out-File $out -Append -Encoding utf8
try { & $fly apps show urban-bot | Out-File $out -Append -Encoding utf8 } catch { "apps show failed: $_" | Out-File $out -Append -Encoding utf8 }
"=== SECRETS LIST ===" | Out-File $out -Append -Encoding utf8
try { & $fly secrets list -a urban-bot | Out-File $out -Append -Encoding utf8 } catch { "secrets list failed: $_" | Out-File $out -Append -Encoding utf8 }
"=== DONE ===" | Out-File $out -Append -Encoding utf8
