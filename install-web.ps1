$ErrorActionPreference = 'Stop'
$NovelRoot = $PSScriptRoot
$Backend = Join-Path $NovelRoot 'web\backend'
$Python = Join-Path $Backend '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $Python)) {
    $BasePython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (!(Test-Path -LiteralPath $BasePython)) { $BasePython = (Get-Command python -ErrorAction Stop).Source }
    & $BasePython -m venv (Join-Path $Backend '.venv')
    if ($LASTEXITCODE -ne 0) { throw '创建 Python 虚拟环境失败' }
}
& $Python -m pip install -r (Join-Path $Backend 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '后端依赖安装失败' }
Push-Location (Join-Path $NovelRoot 'web\frontend')
try { & npm.cmd ci; if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败' } } finally { Pop-Location }
Write-Host '依赖安装完成；没有修改用户 Codex 配置。'
