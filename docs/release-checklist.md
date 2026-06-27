# Release Checklist

Before publishing a release:

1. Test a game as human white.
2. Test a game as human black.
3. Confirm human clock is physical right.
4. Confirm engine clock is physical left.
5. Confirm a human move is accepted only after pressing the right clock button.
6. Confirm the clock stops after a game ends.
7. Confirm the DGT3000 leaves `BT WAIT` soon after activating the Chessnut board.
8. Run syntax checks:

```powershell
python -m py_compile .\files\Eboard.py
python -m py_compile .\files\dgt3000_ble_sidecar.py
```

9. Confirm the repository does not include copied third-party sources or build outputs:

```powershell
git status --ignored
```

Publish these paths:

- `README.md`
- `LICENSE`
- `requirements.txt`
- `install.ps1`
- `uninstall.ps1`
- `stop_clock_sidecar.ps1`
- `files\Eboard.py`
- `files\Eboard.patch`
- `files\dgt3000_ble_sidecar.py`
- `docs\troubleshooting.md`
- `docs\release-checklist.md`
