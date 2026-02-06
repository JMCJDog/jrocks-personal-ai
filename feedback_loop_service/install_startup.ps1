$ErrorActionPreference = "Stop"

$TargetScript = Join-Path $PSScriptRoot "start_watcher.ps1"
$WorkDir = $PSScriptRoot
$ShortcutPath = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\VibeFeedbackWatcher.lnk"

Write-Host "Installing Startup Shortcut..." -ForegroundColor Cyan
Write-Host "Target: $TargetScript"
Write-Host "Location: $ShortcutPath"

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoExit -ExecutionPolicy Bypass -File `"$TargetScript`""
$Shortcut.WorkingDirectory = $WorkDir
$Shortcut.IconLocation = "powershell.exe,0"
$Shortcut.Description = "Vibe Coding Feedback Loop Watcher"
$Shortcut.Save()

Write-Host "Success! The watcher will now start automatically when you log in." -ForegroundColor Green
