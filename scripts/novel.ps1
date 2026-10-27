# Uses an existing runtime; never installs Python or packages.
$novelPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
if (-not (Test-Path -LiteralPath $novelPython)) {
    $novelPython = (Get-Command python -ErrorAction Stop).Source
}
& $novelPython (Join-Path $PSScriptRoot 'novel_workflow.py') @args
exit $LASTEXITCODE
