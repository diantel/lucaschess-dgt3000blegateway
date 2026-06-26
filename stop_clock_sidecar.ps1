$processes = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -like "*dgt3000_ble_sidecar.py*"
}

foreach ($process in $processes) {
    Stop-Process -Id $process.ProcessId -Force
    "Stopped dgt3000_ble_sidecar.py PID $($process.ProcessId)"
}

if (!$processes) {
    "No dgt3000_ble_sidecar.py process found"
}
