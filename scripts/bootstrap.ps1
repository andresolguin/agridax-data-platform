param(
    [switch]$SkipPublish,
    [string]$ComposeProject = "",
    [string]$EnvironmentFile = "",
    [string]$PythonExecutable = "",
    [ValidateRange(1, 600)][int]$ReadinessTimeoutSeconds = 90
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $ProjectRoot
if ($EnvironmentFile) { $env:AGRIDAX_ENV_FILE = (Resolve-Path $EnvironmentFile).Path }
$EnvFile = if ($env:AGRIDAX_ENV_FILE) { $env:AGRIDAX_ENV_FILE } else { Join-Path $ProjectRoot ".env" }
$ComposeArguments = @("--env-file", "$EnvFile")
if ($ComposeProject) { $ComposeArguments += @("--project-name", "$ComposeProject") }
$PythonExe = if ($PythonExecutable) { $PythonExecutable } elseif (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } elseif (Test-Path "./.venv/bin/python") { "./.venv/bin/python" } else { "python" }
function Invoke-Checked {
    param([scriptblock]$Command, [string]$Description)
    Write-Host "==> $Description"
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Description failed with exit $LASTEXITCODE" }
}
Invoke-Checked { & $PythonExe -m agridax.config } "Validating private configuration"
Invoke-Checked { docker compose @ComposeArguments config --quiet } "Validating Compose configuration"
Invoke-Checked { docker compose @ComposeArguments up -d --wait --wait-timeout $ReadinessTimeoutSeconds } "Starting PostgreSQL and waiting for authenticated TCP health"
$Arguments = @("-m", "agridax.pipeline", "--initialize", "--seed-baseline", "--readiness-timeout", "$ReadinessTimeoutSeconds")
if ($SkipPublish) { $Arguments += "--skip-publish" }
Invoke-Checked { & $PythonExe @Arguments } "Initializing workload roles; building, testing, checking freshness and promoting"
Write-Host "AgriDax bootstrap completed successfully."
