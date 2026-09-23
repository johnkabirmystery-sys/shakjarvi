$conns = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($conns) {
    foreach ($c in $conns) {
        try {
            Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "Killed PID $($c.OwningProcess)"
        } catch {}
    }
} else {
    Write-Host "No processes found on port 8000"
}

# Also kill any python processes running run.py
Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*run.py*" -or $_.CommandLine -like "*server.py*" -or $_.CommandLine -like "*uvicorn*"
} | ForEach-Object {
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    Write-Host "Killed python PID $($_.Id)"
}

Write-Host "All Jarvis processes killed."
