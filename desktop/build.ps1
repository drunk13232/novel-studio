param([string]$VersionDirectory = '', [switch]$Preview, [ValidateSet('', 'companion')][string]$ReleaseSuffix = '')
$ErrorActionPreference = 'Stop'
$taskCacheLock=Join-Path $PSScriptRoot '.cache-operation.lock'
$taskCacheHandle=[IO.File]::Open($taskCacheLock,[IO.FileMode]::CreateNew,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)
try {
$ErrorActionPreference = 'Stop'
$taskVersion = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'version.json') -Raw | ConvertFrom-Json
if (-not $VersionDirectory) { $VersionDirectory = 'v' + $taskVersion.version }
if ($VersionDirectory -ne ('v' + $taskVersion.version)) { throw 'Release directory must match desktop/version.json.' }
if ($VersionDirectory -notmatch '^v[0-9]+\.[0-9]+(?:\.[0-9]+)?$') { throw 'Invalid version directory' }
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskEditionDirectory = if ($ReleaseSuffix) { $VersionDirectory + '-' + $ReleaseSuffix } else { $VersionDirectory }
$taskRelease = [IO.Path]::GetFullPath((Join-Path $taskRoot "release\$taskEditionDirectory"))
if (-not $taskRelease.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Invalid release path' }
$taskPython = Join-Path $taskRoot 'web\backend\.venv\Scripts\python.exe'
$taskBuildTemp = Join-Path $taskRoot 'desktop\build\temp'
New-Item -ItemType Directory -Force -Path $taskBuildTemp | Out-Null
$env:TEMP=$taskBuildTemp; $env:TMP=$taskBuildTemp
$env:npm_config_cache=Join-Path $taskRoot 'web\.build-cache\npm'
$env:PYINSTALLER_CONFIG_DIR=Join-Path $taskRoot 'desktop\build\pyinstaller-cache'
if (Test-Path -LiteralPath (Join-Path $taskRelease 'NovelStudio')) { throw 'Release already exists; build to a new directory to preserve old releases.' }
if ($Preview) { $env:NOVEL_PREVIEW_BUILD = '1' } else { Remove-Item Env:NOVEL_PREVIEW_BUILD -ErrorAction SilentlyContinue }
& $taskPython (Join-Path $PSScriptRoot 'fetch_python_runtime.py')
if ($LASTEXITCODE -ne 0) { throw 'Python WASI runtime integrity failed' }
& $taskPython (Join-Path $PSScriptRoot 'collect_licenses.py')
if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
Push-Location (Join-Path $taskRoot 'web\frontend')
try { & npm.cmd run build; if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' } } finally { Pop-Location }
& $taskPython -m PyInstaller --clean --noconfirm --distpath $taskRelease --workpath (Join-Path $taskRoot 'desktop\build') (Join-Path $PSScriptRoot 'NovelStudio.spec')
if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed' }
foreach ($taskNotice in @('LICENSE','NOTICE','COPYRIGHT','THIRD_PARTY_NOTICES.md')) {
 Copy-Item -LiteralPath (Join-Path $taskRoot $taskNotice) -Destination (Join-Path $taskRelease ('NovelStudio\' + $taskNotice))
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'README.txt') -Destination (Join-Path $taskRelease 'NovelStudio\README.txt')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'data-location.public.json') -Destination (Join-Path $taskRelease 'NovelStudio\data-location.json')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'version.json') -Destination (Join-Path $taskRelease 'NovelStudio\version.json')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\core-reliability\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\CORE-RELIABILITY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\literary-core\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\LITERARY-CORE.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\evaluation\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\LITERARY-EVALUATION.md')
if ($Preview) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'PREVIEW-DEMO-GUIDE.md') -Destination (Join-Path $taskRelease 'NovelStudio\PREVIEW-DEMO-GUIDE.md') }
New-Item -ItemType Directory -Force -Path (Join-Path $taskRelease 'NovelStudio\resources') | Out-Null
Set-Content -LiteralPath (Join-Path $taskRelease 'NovelStudio\resources\application.txt') -Value "Novel Studio $VersionDirectory. Production UI: ../_internal/resources/frontend. Licenses: ../_internal/resources/third-party. No private data or credentials included." -Encoding utf8
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\visual-design\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\VISUAL-DESIGN.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\visual-design\DESIGN-SYSTEM.md'),(Join-Path $taskRoot 'docs\visual-design\ASSETS.md') -Destination (Join-Path $taskRelease 'NovelStudio')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\ai-writing-quality\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\AI-WRITING-QUALITY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\long-form\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\LONG-FORM-NARRATIVE.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\worldbuilding-studio\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORLD-BUILDING-STUDIO.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\world-model\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORLD-MODEL-MEMORY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\ai-controls\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\ADVANCED-AI-CONTROLS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\experience-optimization\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\DAILY-EXPERIENCE.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\visual-renaissance\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\THEME-ATELIER.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\visual-renaissance\ASSETS.md') -Destination (Join-Path $taskRelease 'NovelStudio\THEME-ASSETS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\product-evolution\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\PRODUCT-EVOLUTION.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\soft-ui\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\SOFT-UI.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\interaction-freedom\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\INTERACTION-FREEDOM.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\character-control\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\CHARACTER-PYTHON-CONTROL.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\plugin-hub\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\PLUGINS-AND-INTEGRATIONS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\ui-polish\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\UI-REFINEMENT.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\art-refinement\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\ART-REFINEMENT.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\model-control\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\MODEL-CONTROL.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\writing-dashboard\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\WRITING-DASHBOARD.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\daily-writing-tools\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\DAILY-WRITING-TOOLS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-tools\DELIVERY.md') -Destination (Join-Path $taskRelease 'NovelStudio\DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-tools\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\CREATIVE-WORKFLOW.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-tools\HARDENING.md') -Destination (Join-Path $taskRelease 'NovelStudio\HARDENING.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-insights\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\NARRATIVE-INSIGHTS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-insights\DELIVERY-2.22.2.md') -Destination (Join-Path $taskRelease 'NovelStudio\NARRATIVE-INSIGHTS-DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\daily-reliability\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\DAILY-PLANNING.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\daily-reliability\DELIVERY.md') -Destination (Join-Path $taskRelease 'NovelStudio\DAILY-PLANNING-DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\world-first\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORLD-FIRST.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\world-first\DELIVERY.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORLD-FIRST-DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-director\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\CREATIVE-DIRECTOR.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\creative-director\DELIVERY-2.24.2.md') -Destination (Join-Path $taskRelease 'NovelStudio\DIRECTOR-CONSOLE-DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\custom-workflows\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\MY-WORKFLOWS.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\custom-workflows\DELIVERY.md') -Destination (Join-Path $taskRelease 'NovelStudio\MY-WORKFLOWS-DELIVERY.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\workbench-experience\README.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORKBENCH-EXPERIENCE.md')
Copy-Item -LiteralPath (Join-Path $taskRoot 'docs\workbench-experience\DELIVERY-2.24.8.md') -Destination (Join-Path $taskRelease 'NovelStudio\WORKBENCH-VERIFICATION.md')
if ($Preview) { & $taskPython (Join-Path $PSScriptRoot 'package_zip.py') --release-root $taskRelease --preview } else { & $taskPython (Join-Path $PSScriptRoot 'package_zip.py') --release-root $taskRelease }
if ($LASTEXITCODE -ne 0) { throw 'Release audit/ZIP failed' }
& $taskPython (Join-Path $PSScriptRoot 'package_source.py') --release-root $taskRelease
if ($LASTEXITCODE -ne 0) { throw 'Developer source package failed' }


} finally {
 $taskCacheHandle.Dispose()
 Remove-Item -LiteralPath $taskCacheLock -ErrorAction SilentlyContinue
}
