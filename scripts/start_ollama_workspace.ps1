# Start the workspace-local Ollama instance used for bge-m3.
# This does not modify the system-wide Ollama service or D:\Ollama\Models.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$models = Join-Path $root "workspace\ollama_models"
$ollama = "D:\Ollama\App\ollama.exe"

if (-not (Test-Path $ollama)) {
    throw "Ollama executable not found: $ollama"
}
New-Item -ItemType Directory -Force -Path $models | Out-Null

$env:OLLAMA_HOST = "127.0.0.1:11435"
$env:OLLAMA_MODELS = $models
$env:HTTP_PROXY = ""
$env:HTTPS_PROXY = ""
$env:ALL_PROXY = ""
$env:NO_PROXY = "*"

Write-Host "OLLAMA_HOST=$env:OLLAMA_HOST"
Write-Host "OLLAMA_MODELS=$env:OLLAMA_MODELS"
& $ollama serve
