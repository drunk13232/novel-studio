param([int]$Port = 8765, [switch]$NoBrowser, [switch]$Install)
$ErrorActionPreference = 'Stop'
$NovelRoot = $PSScriptRoot
$Backend = Join-Path $NovelRoot 'web\backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
$Frontend = Join-Path $NovelRoot 'web\frontend'
$Runtime = Join-Path $NovelRoot 'web\.runtime'
if ($Port -ne 8765) { throw 'V0.1 固定使用 8765，避免来源配置不一致。' }
if ($Install -or !(Test-Path -LiteralPath $Python) -or !(Test-Path -LiteralPath (Join-Path $Frontend 'node_modules'))) {
    & (Join-Path $NovelRoot 'install-web.ps1')
    if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }
}
try {
    $Existing = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2
    if ($Existing.workspace -eq $NovelRoot) {
        Write-Host '控制台已启动：http://127.0.0.1:8765'
        if (!$NoBrowser) { Start-Process 'http://127.0.0.1:8765' }
        return
    }
    throw '端口被其他服务占用'
} catch {
    if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) { throw '8765 已被占用，请先检查对应服务。' }
}
Push-Location $Frontend
try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw '前端构建失败' } } finally { Pop-Location }
New-Item -ItemType Directory -Path $Runtime -Force | Out-Null
$Server = Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port',"$Port") -WorkingDirectory $Backend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $Runtime 'server.out.log') -RedirectStandardError (Join-Path $Runtime 'server.err.log') -PassThru
@{pid=$Server.Id;workspace=$NovelRoot;port=$Port;started_at=(Get-Date).ToString('o');python=$Python} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Runtime 'server.json') -Encoding UTF8
for ($Attempt=0; $Attempt -lt 40; $Attempt++) {
    Start-Sleep -Milliseconds 500
    if ($Server.HasExited) { throw '后端启动失败；查看 web\.runtime\server.err.log' }
    try { $Ready = Invoke-RestMethod "http://127.0.0.1:$Port/api/health" -TimeoutSec 1; break } catch { }
}
if (!$Ready) { throw '后端启动超时；查看 web\.runtime\server.err.log' }
Write-Host "Novel Web Console: http://127.0.0.1:$Port"
if (!$NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
