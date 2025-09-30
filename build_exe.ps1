# PowerShell build script to create a Windows EXE using PyInstaller
# Usage:
#   1) Open PowerShell in this folder
#   2) Run:  ./build_exe.ps1
# Result:
#   - One-file GUI exe at: dist/Muhasebe.exe

param(
    [switch]$OneDir,   # build as folder instead of one-file
    [string]$Icon,     # optional .ico path (defaults to app.ico if exists)
    [string]$PythonPath # optional full path to python.exe
)

$ErrorActionPreference = 'Stop'

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
    $candidates = @(
        @('py','-3.13'),  # prefer exact 3.13 if launcher exists
        @('python'),
        @('python3'),
        @('py','-3'),
        @('py')
    )
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

function Initialize-Venv {
    if (-not (Test-Path ".venv")) {
        Write-Host "[+] Creating virtual environment (.venv)" -ForegroundColor Cyan
        $pre = @()
        if ($Global:PythonLauncher -and $Global:PythonLauncher.Count -gt 1) {
            $pre = $Global:PythonLauncher[1..($Global:PythonLauncher.Count-1)]
        }
        & $Global:PythonLauncher[0] @pre '-m' 'venv' '.venv'
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
    Write-Host "[+] Installing/upgrading build tools" -ForegroundColor Cyan
    .\.venv\Scripts\python -m pip install --upgrade pip
    .\.venv\Scripts\python -m pip install --upgrade pyinstaller
    # Optional dependency used in investors screen (collected if present)
    try { .\.venv\Scripts\python -m pip show tkcalendar > $null 2>&1 } catch {}
}

function New-Exe {
    $name = 'Muhasebe'
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

    # Ensure all local scripts (modules) are included (hidden imports)
    try {
        $pyFiles = Get-ChildItem -File -Filter '*.py' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
        foreach ($f in $pyFiles) {
            $mod = [System.IO.Path]::GetFileNameWithoutExtension($f)
            if ($mod -and ($mod -ne 'main')) {
                $commonArgs += @('--hidden-import', $mod)
            }
        }
        # Only add optional third-party hidden imports if installed in venv
        $optMods = @('tkcalendar')
        foreach ($m in $optMods) {
            try {
                & .\.venv\Scripts\python -c "import importlib,sys; sys.exit(0) if importlib.util.find_spec('$m') else sys.exit(1)" > $null 2>&1
                if ($LASTEXITCODE -eq 0) { $commonArgs += @('--hidden-import', $m) }
            } catch {}
        }
    } catch {}

    if ($OneDir) {
        Write-Host "[+] Building onedir app (folder)" -ForegroundColor Cyan
        .\.venv\Scripts\python -m PyInstaller @commonArgs 'main.py'
        Write-Host "[i] Output: dist\$name\$name.exe" -ForegroundColor Green
    } else {
        Write-Host "[+] Building onefile app (single exe)" -ForegroundColor Cyan
        .\.venv\Scripts\python -m PyInstaller @commonArgs '--onefile' 'main.py'
        Write-Host "[i] Output: dist\$name.exe" -ForegroundColor Green
    }
}

try {
    Test-Python
    Initialize-Venv
    & .\.venv\Scripts\python -m pip --version > $null 2>&1
    Install-Tools
    New-Exe @PSBoundParameters
    Write-Host '[OK] Build completed.' -ForegroundColor Green
} catch {
    Write-Host "[x] Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}


