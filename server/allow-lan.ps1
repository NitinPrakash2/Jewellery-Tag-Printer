# One-time setup: let other laptops on the WiFi reach this PC on port 8000.
# Right-click PowerShell -> "Run as Administrator", then run:
#   .\allow-lan.ps1
# To undo later: Remove-NetFirewallRule -DisplayName "Jewellery Tag Printer (8000)"

$Rule = "Jewellery Tag Printer (8000)"
$Existing = Get-NetFirewallRule -DisplayName $Rule -ErrorAction SilentlyContinue
if ($Existing) {
    Write-Output "Rule already exists - nothing to do."
} else {
    New-NetFirewallRule -DisplayName $Rule -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 | Out-Null
    Write-Output "Done. Other laptops can now open http://<this-pc-ip>:8000"
}
