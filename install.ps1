param(
    [string]$LucasRoot = "C:\Program Files (x86)\LucasChessR",
    [switch]$SkipPipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceEboard = Join-Path $ProjectRoot "files\Eboard.py"
$SourceSidecar = Join-Path $ProjectRoot "files\dgt3000_ble_sidecar.py"
$TargetEboard = Join-Path $LucasRoot "bin\Code\Board\Eboard.py"
$TargetDigitalBoards = Join-Path $LucasRoot "bin\OS\win32\DigitalBoards"
$TargetSidecar = Join-Path $TargetDigitalBoards "dgt3000_ble_sidecar.py"
$BackupEboard = Join-Path (Split-Path -Parent $TargetEboard) "Eboard.py.lucas-chessnut-dgt3000-backup"

function Assert-File($Path, $Message) {
    if (!(Test-Path -LiteralPath $Path)) {
        throw $Message
    }
}

Assert-File $SourceEboard "Missing packaged file: $SourceEboard"
Assert-File $SourceSidecar "Missing packaged file: $SourceSidecar"
Assert-File $TargetEboard "Lucas Eboard.py not found. Use -LucasRoot to point at LucasChessR: $TargetEboard"
Assert-File $TargetDigitalBoards "Lucas DigitalBoards folder not found: $TargetDigitalBoards"

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python was not found on PATH. Install Python 3 and enable 'Add Python to PATH'."
}

if (!$SkipPipInstall) {
    python -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
}

if (!(Test-Path -LiteralPath $BackupEboard)) {
    Copy-Item -LiteralPath $TargetEboard -Destination $BackupEboard
    "Created backup: $BackupEboard"
} else {
    "Backup already exists: $BackupEboard"
}

Copy-Item -LiteralPath $SourceEboard -Destination $TargetEboard -Force
Copy-Item -LiteralPath $SourceSidecar -Destination $TargetSidecar -Force

python -m py_compile $TargetEboard
python -m py_compile $TargetSidecar

"Installed Lucas Chessnut DGT3000 Bridge."
"Lucas root: $LucasRoot"
"Set Lucas digital board to: Chessnut"
"Do not select DGT-gon for this bridge."
