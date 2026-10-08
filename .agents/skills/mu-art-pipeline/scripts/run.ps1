$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..\..')).Path
$env:UV_PROJECT_ENVIRONMENT = Join-Path $repoRoot '.venv'
$project = $repoRoot
$uvArgs = @('run', '--project', $project) + $args
& uv @uvArgs
exit $LASTEXITCODE
