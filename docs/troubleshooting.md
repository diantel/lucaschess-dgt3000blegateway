# Troubleshooting

## Clock Stays On BT WAIT

- Confirm the ESP32 gateway is powered and connected to the DGT3000.
- Confirm Windows Bluetooth is enabled.
- Confirm the gateway advertises as `DGT3000-Gateway`.
- Restart Lucas Chess after installation.
- Power-cycle the ESP32 gateway if Windows BLE gets stuck.

Test discovery manually:

```powershell
python .\files\dgt3000_ble_sidecar.py --monitor
```

## Wrong Clock Side Runs

- Lucas digital board must be `Chessnut`.
- Human should always be the DGT3000 right side.
- Bot/engine should always be the DGT3000 left side.
- Restart Lucas after changing digital-board settings.

## Human Move Is Not Accepted

- Make the move on the Chessnut board first.
- Press the right DGT3000 clock button after the move.
- The move can be accepted on the next Lucas clock tick, so a short delay is normal.
- Check `%LOCALAPPDATA%\LucasChessnutDGT3000Bridge\clock_button.json` for button events.

## Lucas Closes Or Crashes

- Make sure you installed the current version from this repository.
- Older experimental builds used a background Python thread to submit moves; this version does not.
- Check `<LucasChessR>\bin\bug.log` and `<LucasChessR>\bin\dgt.log`.

## Clock Keeps Running After Game End

- The sidecar stops the physical clock after about 4 seconds without Lucas clock updates.
- If it does not stop, check `sidecar.stdout.log` for an `inactivity_stop` event.

## Python Or Bleak Errors

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If `python` opens the Microsoft Store, install Python from python.org and enable `Add Python to PATH`.
