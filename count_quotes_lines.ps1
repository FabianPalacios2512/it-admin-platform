$lines = Get-Content 'Invoke-ITDiagnostic.ps1'
$inString = $false
for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $matches = [regex]::Matches($line, '(?<!`)"')
    if (($matches.Count % 2) -ne 0) {
        Write-Host "Odd quotes at Line $($i + 1): $line"
    }
}
