# Start Vibe Coding Watcher
$CurrentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $CurrentDir

# Check for credentials
if (-not (Test-Path "$CurrentDir\credentials.json")) {
    Write-Error "Error: credentials.json not found in $CurrentDir"
    exit 1
}

Write-Host "Starting Vibe Coding Watcher..." -ForegroundColor Green
Write-Host "Log file: $CurrentDir\watcher_debug.log" -ForegroundColor Gray

# Loop to auto-restart if it completely crashes (though python script handles most)
while ($true) {
    try {
        python "$CurrentDir\run_feedback_loop.py"
    }
    catch {
        Write-Error "Script crashed: $_"
    }
    
    Write-Warning "Watcher exited. Restarting in 5 seconds..."
    Start-Sleep -Seconds 5
}
