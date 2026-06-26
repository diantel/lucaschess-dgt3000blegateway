param(
    [string]$LucasRoot = "C:\Program Files (x86)\LucasChessR",
    [switch]$KeepSidecar
)

$ErrorActionPreference = "Stop"

$TargetEboard = Join-Path $LucasRoot "bin\Code\Board\Eboard.py"
$BackupEboard = Join-Path (Split-Path -Parent $TargetEboard) "Eboard.py.lucas-chessnut-dgt3000-backup"
$TargetSidecar = Join-Path $LucasRoot "bin\OS\win32\DigitalBoards\dgt3000_ble_sidecar.py"

if (!(Test-Path -LiteralPath $BackupEboard)) {
    throw "Backup not found: $BackupEboard"
}

Copy-Item -LiteralPath $BackupEboard -Destination $TargetEboard -Force
python -m py_compile $TargetEboard

if (!$KeepSidecar -and (Test-Path -LiteralPath $TargetSidecar)) {
    Remove-Item -LiteralPath $TargetSidecar -Force
}

"Restored Lucas Eboard.py from backup."
if ($KeepSidecar) {
    "Kept sidecar file: $TargetSidecar"
} else {
    "Removed sidecar file if present: $TargetSidecar"
}
