$ErrorActionPreference = "Stop"
$cert = Get-ChildItem -Path Cert:\CurrentUser\My | Where-Object Subject -match "AdminDA-ExchangeOnline" | Select-Object -First 1
if ($cert) {
    $pwd = ConvertTo-SecureString "Admin123" -AsPlainText -Force
    Export-PfxCertificate -Cert $cert -FilePath "C:\Users\Fabian Paternina\Desktop\AdminDA_Exchange_WithKey.pfx" -Password $pwd
    Write-Output "PFX_EXPORTED"
} else {
    Write-Output "CERT_NOT_FOUND"
}
