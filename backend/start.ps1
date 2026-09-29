$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "首次运行：创建虚拟环境并安装依赖..."
    uv sync
}

Write-Host "启动后端服务: http://127.0.0.1:8000 (Swagger: /docs)"
& ".venv\Scripts\python.exe" "main.py"