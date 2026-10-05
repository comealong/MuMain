param(
    [ValidateSet('Debug', 'Release')]
    [string]$Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$depRoot = 'D:\DevTools\MuMain'
$vsRoot = 'D:\Program Files\Microsoft Visual Studio\2022\Community'
$vsDevCmd = Join-Path $vsRoot 'Common7\Tools\VsDevCmd.bat'
$ninja = Join-Path $vsRoot 'Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe'
$cmakeRoot = Join-Path $depRoot 'cmake-4.4.3\cmake-4.4.3-windows-x86_64'
$cmake = Join-Path $cmakeRoot 'bin\cmake.exe'
$vcpkgRoot = Join-Path $depRoot 'vcpkg'
$dotnetRoot = Join-Path $depRoot 'dotnet'
$dotnet = Join-Path $dotnetRoot 'dotnet.exe'
$gitBash = 'C:\Program Files\Git\usr\bin\bash.exe'

foreach ($requiredPath in @($vsDevCmd, $ninja, $cmake, $dotnet, $vcpkgRoot, $gitBash)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
        throw "Required build tool is missing: $requiredPath. See docs/build/windows/local-msvc-d-drive.md for setup."
    }
}

$sdkList = & $dotnet --list-sdks
if ($LASTEXITCODE -ne 0 -or -not ($sdkList -match '^10\.')) {
    throw ".NET 10 SDK was not found under $dotnetRoot. See docs/build/windows/local-msvc-d-drive.md for setup."
}

# Import the x64 compiler environment so this works from ordinary PowerShell.
$vsCommand = 'call "' + $vsDevCmd + '" -arch=amd64 -host_arch=amd64 >nul && set'
$vsEnvironment = & $env:ComSpec /d /c $vsCommand
if ($LASTEXITCODE -ne 0) {
    throw "Could not initialize the Visual Studio compiler environment with $vsDevCmd."
}
foreach ($line in $vsEnvironment) {
    if ($line -match '^([^=]+)=(.*)$') {
        Set-Item -Path ("Env:" + $matches[1]) -Value $matches[2]
    }
}

$env:VCPKG_ROOT = $vcpkgRoot
$env:VCPKG_DOWNLOADS = Join-Path $depRoot 'downloads'
$env:VCPKG_DEFAULT_BINARY_CACHE = Join-Path $depRoot 'binary-cache'
$env:DOTNET_ROOT = $dotnetRoot
$env:PATH = "$dotnetRoot;$($cmakeRoot)\bin;$vcpkgRoot;$env:PATH"

$cacheDirectories = @(
    (Join-Path $depRoot 'manifest'),
    (Join-Path $depRoot 'vcpkg_installed'),
    (Join-Path $depRoot 'downloads'),
    (Join-Path $depRoot 'binary-cache'),
    (Join-Path $depRoot 'nuget'),
    (Join-Path $depRoot 'fetchcontent')
)
foreach ($directory in $cacheDirectories) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

# Add the baseline required by current vcpkg to a machine-local manifest copy.
$baseline = (& git -c "safe.directory=$vcpkgRoot" -C $vcpkgRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $baseline) {
    throw "Could not read the vcpkg baseline from $vcpkgRoot."
}
$manifest = Get-Content -Raw (Join-Path $repoRoot 'vcpkg.json') | ConvertFrom-Json
$manifest | Add-Member -NotePropertyName 'builtin-baseline' -NotePropertyValue $baseline -Force
$manifestPath = Join-Path $depRoot 'manifest\vcpkg.json'
$manifestJson = $manifest | ConvertTo-Json -Depth 20
$existingManifest = if (Test-Path -LiteralPath $manifestPath) {
    (Get-Content -Raw $manifestPath).Trim()
} else {
    ''
}
if ($existingManifest -ne $manifestJson.Trim()) {
    $manifestJson | Set-Content -Encoding utf8 $manifestPath
}

# The player build needs SDL's pinned submodule. Initialize it when absent.
$sdlCMakeLists = Join-Path $repoRoot 'src\ThirdParty\SDL\CMakeLists.txt'
if (-not (Test-Path -LiteralPath $sdlCMakeLists)) {
    $env:MU_REPO_ROOT = $repoRoot.Replace('\', '/')
    $submoduleCommand = 'set -e; export PATH="/mingw64/libexec/git-core:$PATH"; export GIT_CONFIG_COUNT=1; export GIT_CONFIG_KEY_0=safe.directory; export GIT_CONFIG_VALUE_0="$MU_REPO_ROOT"; export GIT_EXEC_PATH=/mingw64/libexec/git-core; cd "$(cygpath -u "$MU_REPO_ROOT")"; git -c core.fsmonitor=false submodule update --init -- src/ThirdParty/SDL'
    & $gitBash -c $submoduleCommand
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $sdlCMakeLists)) {
        throw 'Could not initialize the SDL submodule. Check Git/network access and retry.'
    }
}

Push-Location $repoRoot
try {
    $configureArguments = @('--preset', 'windows-x64', '-B', 'out/build/windows-x64')
    $cacheFile = Join-Path $repoRoot 'out\build\windows-x64\CMakeCache.txt'
    if (Test-Path -LiteralPath $cacheFile) {
        $cachedVcpkgRoot = Select-String -Path $cacheFile -Pattern '^Z_VCPKG_ROOT_DIR:INTERNAL=(.*)$' |
            Select-Object -First 1
        if ($cachedVcpkgRoot) {
            $cachedRootValue = $cachedVcpkgRoot.Matches[0].Groups[1].Value.Replace('/', '\').TrimEnd('\')
            if ($cachedRootValue -ine $vcpkgRoot.TrimEnd('\')) {
                $configureArguments += '-UZ_VCPKG_ROOT_DIR'
            }
        }
    }
    $configureArguments += @(
        '-DVCPKG_MANIFEST_DIR=D:/DevTools/MuMain/manifest',
        '-DVCPKG_INSTALLED_DIR=D:/DevTools/MuMain/vcpkg_installed',
        '-DMU_NUGET_CACHE_DIR=D:/DevTools/MuMain/nuget',
        '-DFETCHCONTENT_BASE_DIR=D:/DevTools/MuMain/fetchcontent',
        "-DCMAKE_MAKE_PROGRAM=$($ninja.Replace('\', '/'))"
    )
    & $cmake @configureArguments
    if ($LASTEXITCODE -ne 0) {
        throw 'CMake configure failed.'
    }

    $buildPreset = "windows-x64-$($Configuration.ToLowerInvariant())"
    & $cmake --build --preset $buildPreset --parallel 4
    if ($LASTEXITCODE -ne 0) {
        throw 'CMake build failed.'
    }

    Write-Host "Build succeeded: out/build/windows-x64/src/$Configuration/Main.exe"
}
finally {
    Pop-Location
}
