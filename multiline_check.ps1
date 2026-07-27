$content = Get-Content 'Invoke-ITDiagnostic.ps1' -Raw
$inString = $false
$startLine = 0
$lines = $content -split "`r`n"
for ($i=0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $j = 0
    while ($j -lt $line.Length) {
        if ($line[$j] -eq '`') {
            $j++
        } elseif ($line[$j] -eq '"') {
            if (-not $inString) {
                $inString = $true
                $startLine = $i + 1
            } else {
                $inString = $false
                if ($i + 1 -ne $startLine) {
                    Write-Host "Multi-line string from line $startLine to $($i + 1)"
                }
            }
        }
        $j++
    }
}
if ($inString) {
    Write-Host "Unclosed string starting at line $startLine"
}
