param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,

    [int]$MaxCpuCount = 1,

    [switch]$KillDotnet,

    [switch]$SkipCleanup,

    [Parameter(Mandatory = $true)]
    [string[]]$Command
)

$ErrorActionPreference = "Stop"

function Invoke-DotnetCleanup {
    if ($SkipCleanup) {
        return
    }

    dotnet build-server shutdown | Out-Host

    $processNames = @("VBCSCompiler", "testhost")
    if ($KillDotnet) {
        $processNames += "dotnet"
    }

    foreach ($processName in $processNames) {
        Get-Process -Name $processName -ErrorAction SilentlyContinue |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

function Add-MaxCpuCount {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RawCommand
    )

    $trimmed = $RawCommand.Trim()
    if ($trimmed -notmatch '^(?i)dotnet\s+(build|test)\b') {
        return $RawCommand
    }

    if ($trimmed -match '(\s|^)(-m|/m)(:|\s|$)' -or $trimmed -match '(\s|^)-maxcpucount(:|\s|$)') {
        return $RawCommand
    }

    return "$RawCommand -m:$MaxCpuCount"
}

Push-Location -LiteralPath $ProjectRoot
try {
    Invoke-DotnetCleanup

    foreach ($rawCommand in $Command) {
        $effectiveCommand = Add-MaxCpuCount -RawCommand $rawCommand
        Write-Host ">>> $effectiveCommand"
        & $env:ComSpec /d /s /c $effectiveCommand
        $exitCode = $LASTEXITCODE

        if ($exitCode -ne 0) {
            Invoke-DotnetCleanup
            Write-Error "Command failed with exit code ${exitCode}: $effectiveCommand"
            exit $exitCode
        }
    }
}
finally {
    Pop-Location
}
