[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string[]] $Path
)

$ErrorActionPreference = 'Stop'

$certificateBase64 = $env:WINDOWS_CERTIFICATE_BASE64
$certificatePassword = $env:WINDOWS_CERTIFICATE_PASSWORD
$timestampUrl = $env:WINDOWS_TIMESTAMP_URL

if ([string]::IsNullOrWhiteSpace($certificateBase64)) {
    throw 'WINDOWS_CERTIFICATE_BASE64 is required.'
}
if ($null -eq $certificatePassword) {
    throw 'WINDOWS_CERTIFICATE_PASSWORD is required.'
}
if ([string]::IsNullOrWhiteSpace($timestampUrl)) {
    throw 'WINDOWS_TIMESTAMP_URL is required.'
}

$certificatePath = Join-Path $env:RUNNER_TEMP 'nfprogress-signing.pfx'
try {
    try {
        $certificateBytes = [Convert]::FromBase64String($certificateBase64)
    }
    catch {
        throw 'WINDOWS_CERTIFICATE_BASE64 is not valid base64.'
    }
    [IO.File]::WriteAllBytes($certificatePath, $certificateBytes)

    foreach ($candidate in $Path) {
        $resolved = (Resolve-Path -LiteralPath $candidate -ErrorAction Stop).Path
        if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne '.exe') {
            throw "Only .exe files may be Authenticode-signed: $resolved"
        }

        & signtool sign /fd SHA256 /f $certificatePath /p $certificatePassword `
            /tr $timestampUrl /td SHA256 /a $resolved
        if ($LASTEXITCODE -ne 0) {
            throw "signtool failed for $resolved with exit code $LASTEXITCODE."
        }

        $signature = Get-AuthenticodeSignature -LiteralPath $resolved
        if ($signature.Status -ne 'Valid') {
            throw "Authenticode verification failed for $resolved: $($signature.Status)."
        }
    }
}
finally {
    if (Test-Path -LiteralPath $certificatePath) {
        Remove-Item -LiteralPath $certificatePath -Force
    }
}
