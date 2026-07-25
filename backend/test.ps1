Continue = 'Stop'
 = ConvertTo-SecureString 'Hogar2025*' -AsPlainText -Force
 = New-Object System.Management.Automation.PSCredential ('hogarymoda\administrador', )

Invoke-Command -ComputerName '192.168.1.59' -Credential  -ScriptBlock {
     = Get-PrinterDriver | Select-Object -ExpandProperty Name
    
} | ConvertTo-Json -Compress
