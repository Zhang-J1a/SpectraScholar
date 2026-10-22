param(
    [string]$OllamaExe = "ollama",
    [string]$ModelsDir = (Join-Path (Split-Path -Parent $PSScriptRoot) "workspace\ollama_models"),
    [int]$Port = 11435
)

# Start a separate Ollama process with a project-local model directory.
# It does not modify the system-wide Ollama service or its model directory.
$ErrorActionPreference = "Stop"

$resolved = Get-Command $OllamaExe -ErrorAction SilentlyContinue
if ($null -eq $resolved) {
    if (-not (Test-Path $OllamaExe)) {
        throw "Ollama executable not found: $OllamaExe. Pass -OllamaExe <absolute path>."
    }
} else {
    $OllamaExe = $resolved.Source
}

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

$env:OLLAMA_HOST = "127.0.0.1:$Port"
$env:OLLAMA_MODELS = (Resolve-Path $ModelsDir).Path
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
$env:NO_PROXY = "*"

Write-Host "OLLAMA_HOST=$env:OLLAMA_HOST"
Write-Host "OLLAMA_MODELS=$env:OLLAMA_MODELS"
& $OllamaExe serve
