$ErrorActionPreference = 'Stop'
$Record = Join-Path $PSScriptRoot 'web\.runtime\server.json'
if (!(Test-Path -LiteralPath $Record)) { Write-Host '没有本项目启动记录'; return }
$ServerRecord = Get-Content -LiteralPath $Record -Raw | ConvertFrom-Json
$ServerProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$($ServerRecord.pid)"
if (!$ServerProcess) { Write-Host '服务已经停止'; return }
if ($ServerRecord.workspace -ne $PSScriptRoot -or $ServerProcess.ExecutablePath -ne $ServerRecord.python -or $ServerProcess.CommandLine -notmatch 'uvicorn app.main:app' -or $ServerProcess.CommandLine -notmatch '--port 8765') { throw 'PID 身份不匹配，拒绝终止' }
Stop-Process -Id $ServerRecord.pid
Write-Host '本项目 Web 服务已停止；其他 Codex 进程未受影响。'
