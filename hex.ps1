$line = (Get-Content 'Invoke-ITDiagnostic.ps1')[668]
$bytes = [System.Text.Encoding]::UTF8.GetBytes($line)
Write-Host ([BitConverter]::ToString($bytes))
