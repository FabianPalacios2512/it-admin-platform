$content = Get-Content 'Invoke-ITDiagnostic.ps1' -Raw
# Count " that are not escaped by `
$matches = [regex]::Matches($content, '(?<!`)""?')
Write-Host "Total quotes: $($matches.Count)"
