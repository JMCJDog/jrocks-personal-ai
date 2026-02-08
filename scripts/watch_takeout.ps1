# Google Takeout Watcher Script
# Monitors Downloads folder every 15 minutes for Takeout files
# Moves them to the project's data/takeout/ folder

$DownloadsPath = "$env:USERPROFILE\Downloads"
$ProjectPath = "c:\Users\jared\Vibe Coding (root)\Projects\jrocks-personal-ai"
$DestinationPath = "$ProjectPath\data\takeout"
$LogPath = "$ProjectPath\data\takeout_watcher.log"

# Create destination if not exists
if (!(Test-Path $DestinationPath)) {
    New-Item -ItemType Directory -Path $DestinationPath -Force | Out-Null
}

function Write-Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Out-File -Append -FilePath $LogPath
    Write-Host "$timestamp - $Message"
}

function Process-TakeoutFiles {
    Write-Log "Scanning Downloads folder..."
    
    # Look for Takeout zip files
    $zips = Get-ChildItem -Path $DownloadsPath -Filter "takeout*.zip" -ErrorAction SilentlyContinue
    
    foreach ($zip in $zips) {
        Write-Log "Found Takeout ZIP: $($zip.Name)"
        
        # Extract to destination
        $extractPath = "$DestinationPath\$($zip.BaseName)"
        if (!(Test-Path $extractPath)) {
            Write-Log "Extracting to $extractPath..."
            Expand-Archive -Path $zip.FullName -DestinationPath $extractPath -Force
            Write-Log "Extraction complete!"
            
            # Move original zip to destination
            Move-Item -Path $zip.FullName -Destination "$DestinationPath\$($zip.Name)" -Force
            Write-Log "Moved ZIP to project folder."
        }
    }
    
    # Look for already-extracted Takeout folders
    $folders = Get-ChildItem -Path $DownloadsPath -Directory -Filter "Takeout*" -ErrorAction SilentlyContinue
    
    foreach ($folder in $folders) {
        Write-Log "Found Takeout folder: $($folder.Name)"
        $destFolder = "$DestinationPath\$($folder.Name)"
        
        if (!(Test-Path $destFolder)) {
            Write-Log "Moving folder to project..."
            Move-Item -Path $folder.FullName -Destination $destFolder -Force
            Write-Log "Move complete!"
        }
    }
    
    # Check for mbox files directly
    $mboxFiles = Get-ChildItem -Path $DownloadsPath -Filter "*.mbox" -ErrorAction SilentlyContinue
    foreach ($mbox in $mboxFiles) {
        Write-Log "Found MBOX file: $($mbox.Name)"
        $destMbox = "$DestinationPath\$($mbox.Name)"
        if (!(Test-Path $destMbox)) {
            Move-Item -Path $mbox.FullName -Destination $destMbox -Force
            Write-Log "Moved MBOX to project."
        }
    }
    
    # Check for VCF (contacts) files
    $vcfFiles = Get-ChildItem -Path $DownloadsPath -Filter "*.vcf" -ErrorAction SilentlyContinue
    foreach ($vcf in $vcfFiles) {
        Write-Log "Found Contacts file: $($vcf.Name)"
        Move-Item -Path $vcf.FullName -Destination "$DestinationPath\$($vcf.Name)" -Force
        Write-Log "Moved VCF to project."
    }
}

# Calculate end time (6 AM tomorrow)
$endTime = (Get-Date).Date.AddDays(1).AddHours(6)
Write-Log "=== Takeout Watcher Started ==="
Write-Log "Monitoring: $DownloadsPath"
Write-Log "Destination: $DestinationPath"
Write-Log "Will run until: $endTime"
Write-Log "Interval: 15 minutes"

# Initial scan
Process-TakeoutFiles

# Loop until 6 AM
while ((Get-Date) -lt $endTime) {
    Write-Log "Sleeping for 15 minutes..."
    Start-Sleep -Seconds 900  # 15 minutes
    Process-TakeoutFiles
}

Write-Log "=== Watcher Stopped (Reached end time) ==="
