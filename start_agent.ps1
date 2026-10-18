$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    throw "未找到虚拟环境 Python：$python"
}

Set-Location $projectRoot
& $python -m agent.PrimaryAgent
