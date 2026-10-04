$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$localVenv = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localVenv) { $demoPython = $localVenv }
else { $demoPython = (Get-Command python -ErrorAction Stop).Source }
Write-Host 'Dang mo ung dung Python MPRNet...'
& $demoPython -X utf8 desktop.py
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Xem README.md de cai dat Python va thu vien.'
    Read-Host 'Nhan Enter de dong'
    exit 1
}
