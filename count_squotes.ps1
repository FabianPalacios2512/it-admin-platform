$lines = Get-Content 'Invoke-ITDiagnostic.ps1'
$inString = $false
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $matches = [regex]::Matches($line, "([`'])")
    $count = 0
    foreach ($m in $matches) {
        if ($m.Value -eq "'") {
            $count++
        }
    }
    if (($count % 2) -ne 0) {
        Write-Host "Odd single quotes at Line $($i + 1): $line"
    }
}
