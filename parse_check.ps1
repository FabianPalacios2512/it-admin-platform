$errors = $null
$tokens = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $PWD 'Invoke-ITDiagnostic.ps1'), [ref]$tokens, [ref]$errors)
if ($errors) {
    foreach ($e in $errors) {
        Write-Host "Error: $($e.Message) at Line $($e.Extent.StartLineNumber)"
    }
} else {
    Write-Host "Syntax OK"
}
