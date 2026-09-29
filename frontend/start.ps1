$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

if (-not (Test-Path "node_modules")) {
    Write-Host "首次运行：安装前端依赖..."
    npm install
}

Write-Host "启动前端服务: http://localhost:5173"
npm run dev