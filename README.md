# Lucas Chessnut DGT3000 Bridge

Use a Chessnut board over USB in Lucas Chess R while controlling a real DGT3000 clock through Tortue95's `DGT3000-BLE-Gateway`.

This is not a replacement digital-board DLL. Lucas still uses its native `Chessnut` driver for the board. This project adds a small Python BLE sidecar and patches Lucas' `Eboard.py` so the physical DGT3000 clock behaves like a real game clock.

## Features

- Chessnut board stays connected through Lucas' native USB driver.
- DGT3000 clock connects through `DGT3000-BLE-Gateway` over Bluetooth LE.
- Human clock is always on the physical right side.
- Engine/bot clock is always on the physical left side.
- Human moves are held until the right DGT3000 clock button is pressed.
- Unequal side times and increments are supported through Lucas' own clock values.
- The physical clock stops automatically when Lucas stops updating after game end.

## Requirements

- Windows.
- Lucas Chess R installed.
- Python 3 available as `python` in PowerShell.
- Chessnut board connected by USB.
- DGT3000 clock connected to an ESP32 running Tortue95's `DGT3000-BLE-Gateway`.
- The gateway advertising as `DGT3000-Gateway`.

Install the Python dependency manually if needed:

```powershell
python -m pip install -r requirements.txt
```

The installer also tries to install this dependency.

## Installation

1. Close Lucas Chess.
2. Download or clone this repository.
3. Open PowerShell as Administrator.
4. From this folder, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

If Lucas Chess is installed somewhere else:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -LucasRoot "D:\Path\To\LucasChessR"
```

The installer will:

- back up `Eboard.py`,
- install the patched `Eboard.py`,
- install `dgt3000_ble_sidecar.py`,
- install `bleak`,
- compile-check the installed Python files.

## Lucas Chess Setup

1. Start Lucas Chess.
2. Set the digital board to `Chessnut`.
3. Do not select `DGT-gon` for this bridge.
4. Connect the Chessnut board over USB.
5. Power the ESP32 DGT3000 BLE gateway and connect it to the DGT3000.
6. Start a game against an engine.

## Usage

- Physical DGT3000 left side: engine/bot.
- Physical DGT3000 right side: human.
- Make the human move on the Chessnut board.
- Press the right DGT3000 clock button.
- Lucas accepts the move and starts the engine clock.
- When the engine moves, Lucas updates the board and starts the human clock.

## Uninstall

Close Lucas Chess, then run PowerShell as Administrator:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

Or specify a custom Lucas path:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1 -LucasRoot "D:\Path\To\LucasChessR"
```

## Logs

Runtime files are written to:

```text
%LOCALAPPDATA%\LucasChessnutDGT3000Bridge
```

Useful logs:

- `sidecar.stdout.log`
- `sidecar.stderr.log`
- `clock_request.json`
- `clock_button.json`

Lucas patch diagnostics are written to:

```text
<LucasChessR>\bin\dgt.log
```

## Troubleshooting

See `docs\troubleshooting.md`.

## Notes

- This project modifies Lucas Chess' installed `Eboard.py`; keep the generated backup.
- The installer is designed for Lucas Chess R on Windows.
- This repository does not redistribute Lucas Chess or Chessnut/DGT firmware.
