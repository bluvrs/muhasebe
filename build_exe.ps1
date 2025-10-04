# PowerShell build script to create a Windows EXE using PyInstaller
# Usage:
#   1) Open PowerShell in this folder
#   2) Run:
#        ./build_exe.ps1                   # auto-detect Python (keeps existing .venv)
#        ./build_exe.ps1 -Arch x64         # force 64-bit build (uses .venv-x64)
#        ./build_exe.ps1 -Arch x86         # force 32-bit build (uses .venv-x86)
#        ./build_exe.ps1 -Icon app.ico     # custom icon
#        ./build_exe.ps1 -OneDir           # folder output instead of onefile
#        ./build_exe.ps1 -Arch x86 -Win7Compat   # build compatible for Windows 7 (32-bit)
# Result:
#   - One-file GUI exe at: dist/Muhasebe.exe

param(
    [switch]$OneDir,   # build as folder instead of one-file
    [string]$Icon,     # optional .ico path (defaults to app.ico if exists)
    [string]$PythonPath, # optional full path to python.exe
    [ValidateSet('auto','x86','x64')]
    [string]$Arch = 'auto', # target architecture; 'auto' uses whichever Python is selected
    [switch]$Win7Compat     # prefer Python 3.8 and PyInstaller compatible with Windows 7
)

$ErrorActionPreference = 'Stop'

# --- Version helpers ---
function Update-VersionFile {
    $verPath = Join-Path (Get-Location) 'VERSION.txt'
    if (-not (Test-Path $verPath)) {
        '1.00' | Out-File -FilePath $verPath -Encoding UTF8 -Force
    }
    try {
        $cur = (Get-Content -Path $verPath -ErrorAction Stop | Select-Object -First 1).Trim()
        if (-not $cur) { $cur = '1.00' }
    } catch { $cur = '1.00' }
    # Parse and bump by 0.01
    try {
        $dec = [decimal]::Parse($cur, [System.Globalization.CultureInfo]::InvariantCulture)
        $dec = $dec + 0.01
        $new = $dec.ToString('0.00', [System.Globalization.CultureInfo]::InvariantCulture)
    } catch {
        $new = '1.00'
    }
    $new | Out-File -FilePath $verPath -Encoding UTF8 -Force
    Write-Host "[i] Version bumped: $cur -> $new" -ForegroundColor DarkCyan
    return $new
}

# Resolve Python launcher (python, py -3, or py)
$Global:PythonLauncher = $null  # e.g. @('python') or @('py','-3')
function Resolve-Python {
    # 1) If explicit PythonPath provided
    if ($PythonPath -and (Test-Path $PythonPath)) {
        $Global:PythonLauncher = @($PythonPath)
        return $true
    }
    # 2) Probe common install directories to avoid WindowsApps alias
    try {
        $commonBases = @(
            Join-Path $env:LOCALAPPDATA 'Programs\Python',
            'C:\\Program Files\\Python',
            'C:\\Program Files (x86)\\Python'
        ) | Where-Object { Test-Path $_ }
        foreach ($base in $commonBases) {
            $dirs = Get-ChildItem -Path $base -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
            foreach ($d in $dirs) {
                $pex = Join-Path $d.FullName 'python.exe'
                if (Test-Path $pex) {
                    $Global:PythonLauncher = @($pex)
                    return $true
                }
            }
        }
    } catch { }
    # 3) Try PATH candidates (skip WindowsApps alias)
    $candidates = @()
    if ($Arch -eq 'x86') {
        if ($Win7Compat) {
            $candidates += @(@('py','-3.8-32'))
        } else {
            $candidates += @(@('py','-3.13-32'), @('py','-3-32'))
        }
    } elseif ($Arch -eq 'x64') {
        if ($Win7Compat) {
            $candidates += @(@('py','-3.8-64'))
        } else {
            $candidates += @(@('py','-3.13-64'), @('py','-3-64'))
        }
    }
    # generic fallbacks regardless of Arch
    $generic = @(
        @('py','-3.13'),  # prefer exact 3.13 if launcher exists
        @('python'),
        @('python3'),
        @('py','-3'),
        @('py')
    )
    if ($Win7Compat) {
        # push 3.8 to the front of generic fallbacks for Win7 builds
        $candidates += @(@('py','-3.8'), @('py','-3.8-32'), @('py','-3.8-64'))
    }
    $candidates += $generic
    foreach ($cand in $candidates) {
        try {
            $pyArgs = @()
            if ($cand.Count -gt 1) { $pyArgs += $cand[1..($cand.Count-1)] }
            $pyArgs += '-V'
            & $cand[0] @pyArgs | Out-Null
            try {
                $cmd = Get-Command $cand[0] -ErrorAction Stop
                if ($cmd -and ($cmd.Source -like '*WindowsApps*')) { throw 'WindowsApps alias' }
            } catch { continue }
            $Global:PythonLauncher = $cand
            return $true
        } catch { }
    }
    return $false
}

function Get-PythonArch {
    # Returns 'x86' or 'x64' for the selected launcher
    $pre = @()
    if ($Global:PythonLauncher -and $Global:PythonLauncher.Count -gt 1) {
        $pre = $Global:PythonLauncher[1..($Global:PythonLauncher.Count-1)]
    }
    $code = "import struct; import sys; sys.stdout.write('x86' if struct.calcsize('P')*8==32 else 'x64')"
    try {
        $out = & $Global:PythonLauncher[0] @pre '-c' $code
        if ($LASTEXITCODE -eq 0 -and ($out -in @('x86','x64'))) { return $out }
    } catch { }
    return 'unknown'
}

function Get-PythonVersionShort {
    $pre = @()
    if ($Global:PythonLauncher -and $Global:PythonLauncher.Count -gt 1) {
        $pre = $Global:PythonLauncher[1..($Global:PythonLauncher.Count-1)]
    }
    $code = "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
    try {
        $out = & $Global:PythonLauncher[0] @pre '-c' $code
        if ($LASTEXITCODE -eq 0) { return $out.Trim() }
    } catch { }
    return 'unknown'
}

function Get-PythonExePath {
    $pre = @()
    if ($Global:PythonLauncher -and $Global:PythonLauncher.Count -gt 1) {
        $pre = $Global:PythonLauncher[1..($Global:PythonLauncher.Count-1)]
    }
    $code = "import sys; print(sys.executable)"
    try {
        $out = & $Global:PythonLauncher[0] @pre '-c' $code
        if ($LASTEXITCODE -eq 0) { return $out.Trim() }
    } catch { }
    return '<unknown>'
}

function Initialize-Venv {
    param(
        [string]$VenvDir
    )
    if (-not (Test-Path $VenvDir)) {
        Write-Host "[+] Creating virtual environment ($VenvDir)" -ForegroundColor Cyan
        $pre = @()
        if ($Global:PythonLauncher -and $Global:PythonLauncher.Count -gt 1) {
            $pre = $Global:PythonLauncher[1..($Global:PythonLauncher.Count-1)]
        }
        & $Global:PythonLauncher[0] @pre '-m' 'venv' $VenvDir
    }
}

function Test-Python {
    if (-not (Resolve-Python)) {
        Write-Host "[!] Python not found. Install Python 3.9+ and ensure 'python' or 'py' is on PATH." -ForegroundColor Yellow
        Write-Host "    Tip: Disable Windows App Execution Aliases if it launches Microsoft Store." -ForegroundColor Yellow
        Write-Host "    Or run with:  .\\build_exe.ps1 -PythonPath 'C:\\Path\\to\\python.exe'" -ForegroundColor Yellow
        exit 1
    }
}

function Install-Tools {
    param(
        [string]$VenvDir,
        [switch]$Win7Compat
    )
    Write-Host "[+] Installing/upgrading build tools" -ForegroundColor Cyan
    $venvPy = Join-Path $VenvDir 'Scripts\python'
    & $venvPy -m pip install --upgrade pip
    if ($Win7Compat) {
        Write-Host "[i] Pinning PyInstaller to 4.10 for Windows 7 compatibility" -ForegroundColor DarkCyan
        & $venvPy -m pip install "pyinstaller==4.10"
    } else {
        & $venvPy -m pip install --upgrade pyinstaller
    }
    # Ensure reportlab is installed (for PDF generation, if used)
    try { & $venvPy -m pip show reportlab > $null 2>&1 } catch {}
    if ($LASTEXITCODE -ne 0) { & $venvPy -m pip install --upgrade reportlab }
    # Optional dependency used in investors screen (collected if present)
    try { & $venvPy -m pip show tkcalendar > $null 2>&1 } catch {}
}

function New-Exe {
    param(
        [string]$VenvDir,
        [string]$BuildArch
    )
    $name = 'Kooperatif'
    $commonArgs = @(
        '--noconfirm',
        '--clean',
        '--windowed',   # no console window
        "--name=$name"
    )
    # Icon handling (-i <path>)
    $iconPath = $null
    if ($Icon) {
        if (Test-Path $Icon) { $iconPath = (Resolve-Path $Icon).Path }
    } elseif (Test-Path 'app.ico') {
        $iconPath = (Resolve-Path 'app.ico').Path
    }
    if ($iconPath) { $commonArgs += @('-i', $iconPath) }
    # Include Roboto font folder as data (if present)
    if (Test-Path 'Roboto') {
        $commonArgs += @('--add-data','Roboto;Roboto')
    }
        # Include app icon and png for runtime usage
    if (Test-Path 'app.ico') {
        $commonArgs += @('--add-data','app.ico;.')
    }
    if (Test-Path 'app.png') {
        $commonArgs += @('--add-data','app.png;.')
    }
# Include VERSION.txt so app can read runtime version
    if (Test-Path 'VERSION.txt') {
        $commonArgs += @('--add-data','VERSION.txt;VERSION.txt')
    }

    # Ensure all local scripts (modules) are included (hidden imports)
    try {
        $pyFiles = Get-ChildItem -File -Filter '*.py' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
        foreach ($m in $optMods) {
            try {
                $venvPy = Join-Path $VenvDir 'Scripts\python'
                & $venvPy -c "import importlib,sys; sys.exit(0) if importlib.util.find_spec('$m') else sys.exit(1)" > $null 2>&1
                if ($LASTEXITCODE -eq 0) { $commonArgs += @('--hidden-import', $m) }
            } catch {}
        }
    } catch {}

    if ($OneDir) {
        Write-Host "[+] Building onedir app (folder) [$BuildArch]" -ForegroundColor Cyan
        $venvPy = Join-Path $VenvDir 'Scripts\python'
        & $venvPy -m PyInstaller @commonArgs 'main.py'
        Write-Host "[i] Output: dist\$name\$name.exe" -ForegroundColor Green
    } else {
        Write-Host "[+] Building onefile app (single exe) [$BuildArch]" -ForegroundColor Cyan
        $venvPy = Join-Path $VenvDir 'Scripts\python'
        & $venvPy -m PyInstaller @commonArgs '--onefile' 'main.py'
        Write-Host "[i] Output: dist\$name.exe" -ForegroundColor Green
    }
}

try {
    Test-Python
    # Verify bitness and choose venv directory
    $detectedArch = Get-PythonArch
    $detectedVer = Get-PythonVersionShort
    $pyPath = Get-PythonExePath
    if ($Arch -ne 'auto' -and $detectedArch -eq 'unknown') {
        # Try to re-resolve with arch-preferred candidates if we couldn't detect
        if (-not (Resolve-Python)) { throw "Python not found while resolving for requested architecture '$Arch'" }
        $detectedArch = Get-PythonArch
        $detectedVer = Get-PythonVersionShort
        $pyPath = Get-PythonExePath
    }
    if ($Arch -ne 'auto' -and $detectedArch -ne 'unknown' -and $Arch -ne $detectedArch) {
        Write-Host "[!] Requested Arch=$Arch but selected Python is $detectedArch. Trying harder to locate matching Python..." -ForegroundColor Yellow
        # Try to re-resolve with tighter candidates
        $tmpArch = $Arch; $Arch = $tmpArch  # ensure global is set for Resolve-Python to use arch-specific candidates
        if (-not (Resolve-Python)) { throw "Python matching architecture '$tmpArch' not found. Install 32-bit or 64-bit Python accordingly." }
        $detectedArch = Get-PythonArch
        if ($detectedArch -ne $tmpArch) { throw "Resolved Python does not match requested architecture ($tmpArch)." }
    }

    if ($Win7Compat) {
        if ($detectedVer -ne '3.8') {
            throw "Win7Compat requires Python 3.8. Install Python 3.8 ($Arch) and re-run with -Win7Compat."
        }
    }

    # Choose venv dir: keep legacy '.venv' for auto, arch-specific for forced builds
    if ($Arch -eq 'auto') {
        $VenvDir = '.venv'
    } else {
        $suffix = if ($detectedArch -in @('x86','x64')) { $detectedArch } else { $Arch }
        $VenvDir = ".venv-$suffix"
    }

    Initialize-Venv -VenvDir $VenvDir
    $venvPy = Join-Path $VenvDir 'Scripts\python'
    & $venvPy -m pip --version > $null 2>&1
    Install-Tools -VenvDir $VenvDir -Win7Compat:$Win7Compat
    # Bump version file
    $version = Update-VersionFile
    $buildArch = if ($detectedArch -ne 'unknown') { $detectedArch } else { $Arch }
    Write-Host ("[i] Requested Arch={0}; Using Python={1} ({2})" -f $Arch,$detectedArch,$pyPath) -ForegroundColor DarkCyan
    New-Exe -VenvDir $VenvDir -BuildArch $buildArch
    Write-Host '[OK] Build completed.' -ForegroundColor Green
} catch {
    Write-Host "[x] Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}








