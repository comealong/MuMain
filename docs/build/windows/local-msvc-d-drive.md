# Windows - Local MSVC setup on D:

This records the working native x64 Release setup for this machine. Keep the
dependency tools and caches on D:; the checkout and build output stay on E:.
The successful build produced `out/build/windows-x64/src/Release/Main.exe`.

## Quick rebuild

After the D-drive dependencies from the first setup are installed, run this
from the repository root in a regular PowerShell window:

```powershell
.\scripts\build-windows.ps1
```

The script loads the MSVC x64 environment, refreshes the local vcpkg manifest,
configures CMake with the tools and caches on D:, and builds Release. It keeps
the existing build directory, so later runs reuse compiled files. To build
Debug, run `.\scripts\build-windows.ps1 -Configuration Debug`.

Run the client from its output directory so it finds the copied runtime files:

```powershell
Set-Location out/build/windows-x64/src/Release
.\Main.exe
```

## D-drive layout

| Path | Contents |
|------|----------|
| `D:\DevTools\MuMain\dotnet` | .NET 10 SDK (verified as 10.0.401) |
| `D:\DevTools\MuMain\vcpkg` | vcpkg checkout and bootstrap executable |
| `D:\DevTools\MuMain\manifest` | Local copy of `vcpkg.json` with a baseline pinned to this checkout |
| `D:\DevTools\MuMain\vcpkg_installed` | Installed x64 vcpkg dependencies |
| `D:\DevTools\MuMain\downloads` | vcpkg downloads and extracted helper tools |
| `D:\DevTools\MuMain\binary-cache` | vcpkg binary cache |
| `D:\DevTools\MuMain\nuget` | .NET/NuGet package cache |
| `D:\DevTools\MuMain\fetchcontent` | CMake FetchContent sources and build trees |
| `D:\DevTools\MuMain\cmake-4.4.3` | Portable Kitware CMake 4.4.3 archive extraction |

The Visual Studio Ninja executable used by this setup is:
`D:\Program Files\Microsoft Visual Studio\2022\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja\ninja.exe`.

## First-time setup or reconfiguration

Use **Developer PowerShell for VS 2022**. Install the portable tools on D: and
create the cache directories before configuring:

```powershell
$depRoot = 'D:\DevTools\MuMain'
New-Item -ItemType Directory -Force -Path $depRoot | Out-Null

# Install .NET 10 locally. UseBasicParsing suppresses the Windows PowerShell 5
# Invoke-WebRequest security prompt.
Invoke-WebRequest -UseBasicParsing `
  -Uri 'https://dot.net/v1/dotnet-install.ps1' `
  -OutFile "$depRoot\dotnet-install.ps1"
& "$depRoot\dotnet-install.ps1" -Channel 10.0 -InstallDir "$depRoot\dotnet" -NoPath

# Install an independent vcpkg checkout; the VS-bundled instance failed on
# this machine because it requires a registry baseline for manifest mode.
git clone --depth 1 https://github.com/microsoft/vcpkg.git "$depRoot\vcpkg"
& "$depRoot\vcpkg\bootstrap-vcpkg.bat" -disableMetrics

# The current vcpkg ports require CMake 4.4.3. Download the portable ZIP and
# official checksum from Kitware, then verify before extracting.
$downloadDir = "$depRoot\downloads"
New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
Invoke-WebRequest -UseBasicParsing `
  -Uri 'https://cmake.org/files/v4.4/cmake-4.4.3-windows-x86_64.zip' `
  -OutFile "$downloadDir\cmake-4.4.3-windows-x86_64.zip"
Invoke-WebRequest -UseBasicParsing `
  -Uri 'https://cmake.org/files/v4.4/cmake-4.4.3-SHA-256.txt' `
  -OutFile "$downloadDir\cmake-4.4.3-SHA-256.txt"
$hashLine = Get-Content "$downloadDir\cmake-4.4.3-SHA-256.txt" |
  Where-Object { $_ -match 'cmake-4\.4\.3-windows-x86_64\.zip' } |
  Select-Object -First 1
$expected = ([regex]::Match($hashLine, '^[0-9a-fA-F]{64}')).Value.ToUpperInvariant()
$actual = (Get-FileHash "$downloadDir\cmake-4.4.3-windows-x86_64.zip" -Algorithm SHA256).Hash
if (-not $expected -or $actual -ne $expected) { throw 'CMake ZIP SHA-256 mismatch.' }
Expand-Archive "$downloadDir\cmake-4.4.3-windows-x86_64.zip" "$depRoot\cmake-4.4.3"

New-Item -ItemType Directory -Force -Path `
  "$depRoot\manifest", `
  "$depRoot\vcpkg_installed", `
  "$depRoot\binary-cache", `
  "$depRoot\nuget", `
  "$depRoot\fetchcontent" | Out-Null

# vcpkg now requires a baseline. Keep this machine-only copy on D: so the
# repository's vcpkg.json stays unchanged. The baseline must match this clone.
$baseline = (& git -c "safe.directory=$depRoot\vcpkg" `
  -C "$depRoot\vcpkg" rev-parse HEAD).Trim()
$manifest = Get-Content -Raw vcpkg.json | ConvertFrom-Json
$manifest | Add-Member -NotePropertyName 'builtin-baseline' `
  -NotePropertyValue $baseline -Force
$manifest | ConvertTo-Json -Depth 20 |
  Set-Content -Encoding utf8 "$depRoot\manifest\vcpkg.json"

$env:VCPKG_ROOT = "$depRoot\vcpkg"
$env:VCPKG_DOWNLOADS = "$depRoot\downloads"
$env:VCPKG_DEFAULT_BINARY_CACHE = "$depRoot\binary-cache"
$env:DOTNET_ROOT = "$depRoot\dotnet"
$env:PATH = "$env:DOTNET_ROOT;$depRoot\cmake-4.4.3\cmake-4.4.3-windows-x86_64\bin;$env:PATH"
$cmakeRoot = "$depRoot\cmake-4.4.3\cmake-4.4.3-windows-x86_64"
$ninja = 'D:/Program Files/Microsoft Visual Studio/2022/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/Ninja/ninja.exe'

& "$cmakeRoot\bin\cmake.exe" --preset windows-x64 `
  -B out/build/windows-x64 `
  -UZ_VCPKG_ROOT_DIR `
  -DVCPKG_MANIFEST_DIR=D:/DevTools/MuMain/manifest `
  -DVCPKG_INSTALLED_DIR=D:/DevTools/MuMain/vcpkg_installed `
  -DMU_NUGET_CACHE_DIR=D:/DevTools/MuMain/nuget `
  -DFETCHCONTENT_BASE_DIR=D:/DevTools/MuMain/fetchcontent `
  -DCMAKE_MAKE_PROGRAM="$ninja"
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed.' }

& "$cmakeRoot\bin\cmake.exe" --build --preset windows-x64-release --parallel 4
```

`-UZ_VCPKG_ROOT_DIR` clears a stale internal cache entry left by an earlier
configure that used Visual Studio's bundled vcpkg. The other cache paths keep
the installed packages and fetched sources on D:.

## Problems found and fixes

| Symptom | Cause | Fix |
|---------|-------|-----|
| .NET restore rejects `net10.0` | Only .NET 9 was on `PATH` | Install .NET 10 to `D:\DevTools\MuMain\dotnet`; set `DOTNET_ROOT` and put that directory first on `PATH`. |
| `vcpkg install` reports that the manifest needs a baseline | The repository's `vcpkg.json` has no `builtin-baseline`, which the current vcpkg registry requires | Clone/bootstrap standalone vcpkg on D: and use the local manifest copy with `builtin-baseline` set to that clone's commit. Do not add a machine-specific baseline to the repository manifest. |
| `Operation REMOVE_DUPLICATES not recognized` during zlib configure | CMake cache still pointed `Z_VCPKG_ROOT_DIR` at VS's older bundled vcpkg scripts | Reconfigure with `-UZ_VCPKG_ROOT_DIR`; explicitly set `VCPKG_ROOT` to the D-drive clone. |
| vcpkg tries to download CMake 4.4.3, then GitHub returns curl SSL error 35 | VS provided CMake 3.31.6, below the port's requested version; the GitHub release URL failed through the local proxy | Download the portable ZIP and SHA file from Kitware's `cmake.org/files/v4.4/` URL, verify SHA-256, and use CMake 4.4.3 from D:. |
| `VCPKG_DEFAULT_BINARY_CACHE must be a directory` | The environment variable was set before creating its destination | Create `D:\DevTools\MuMain\binary-cache` (and the downloads directory) before configuring. |
| CMake cannot find `Ninja Multi-Config` | VS's Ninja executable was not on the process `PATH` | Pass `-DCMAKE_MAKE_PROGRAM` with the full path shown above, or add the VS Ninja directory to `PATH`. |
| Staging `MUnique.Client.Library.dll` fails with `Permission denied` | A running MU client/server has the staged DLL open | Close the running program and rerun the build command. |
| CMake removes an incomplete `src/ThirdParty/SDL` folder, then Git reports dubious ownership or cannot find `git-sh-setup` | The E: exFAT checkout triggers Git safe-directory checks, and the shell script does not include Git's exec directory in its `PATH` | Initialize SDL from Git Bash with the command below. It sets a per-process safe-directory value and does not modify global Git config. |
| Windows PowerShell 5 shows an `Invoke-WebRequest` security prompt | The cmdlet's default page parser prompts interactively | Always use `-UseBasicParsing`; use `curl.exe` when appropriate. |

MSVC's localized `/showIncludes` output can make Ninja's progress log very
verbose. The include lines are diagnostic noise; continue unless an actual
compiler `error` or nonzero build exit appears.

Initialize only the SDL submodule required by the player build when it is
missing or incomplete:

```powershell
& 'C:\Program Files\Git\usr\bin\bash.exe' -c 'set -e; export PATH="/mingw64/libexec/git-core:$PATH"; export GIT_CONFIG_COUNT=1; export GIT_CONFIG_KEY_0=safe.directory; export GIT_CONFIG_VALUE_0=E:/Projects/MuMain; export GIT_EXEC_PATH=/mingw64/libexec/git-core; git -c core.fsmonitor=false submodule update --init -- src/ThirdParty/SDL; test -f src/ThirdParty/SDL/CMakeLists.txt'
```

The successful Release build also emitted MSVC warning C4477 in
`src/source/Engine/Object/ZzzInfomation.cpp` for `%d` format specifiers used
with `int64_t`; these warnings did not prevent linking `Main.exe`.
