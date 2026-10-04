# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
# Read-only OS signature inspection. Never executes the inspected target.
param([Parameter(Mandatory=$true)][string]$LiteralPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature -LiteralPath $LiteralPath
if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid -or
    $signature.SignatureType.ToString() -ne 'Authenticode' -or
    $null -eq $signature.SignerCertificate -or $null -eq $signature.TimeStamperCertificate) {
    throw 'A valid timestamped embedded publisher signature is required.'
}
$publicKey = $signature.SignerCertificate.PublicKey.ExportSubjectPublicKeyInfo()
$identity = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData($publicKey)).ToLowerInvariant()
$report = @{
    schema = 'augmentor-windows-publisher/1'
    trusted = $true
    timestamped = $true
    publicKeySHA256 = $identity
}
[Console]::Out.WriteLine(($report | Microsoft.PowerShell.Utility\ConvertTo-Json -Compress))
