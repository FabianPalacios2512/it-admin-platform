$lines = Get-Content 'Invoke-ITDiagnostic.ps1'
$level = 0
for ($i = 500; $i -lt 650; $i++) {
    $line = $lines[$i]
    $matchesOpen = [regex]::Matches($line, '\{')
    $matchesClose = [regex]::Matches($line, '\}')
    $level += $matchesOpen.Count - $matchesClose.Count
    Write-Host "Line $($i + 1): Level $level - $line"
}
