# Simple script to attempt repo creation and push, writes JSON report to vibe_create_report.json
$report = [ordered]@{
    created = $false
    pushed = $false
    remote_url = $null
    errors = @()
    commands = @()
}
function R($c) {
    $report.commands += $c
    try {
        $out = & powershell -NoProfile -NonInteractive -Command $c 2>&1
        $rc = $LASTEXITCODE
        if ($rc -ne 0) { $report.errors += "Command failed: $c -- Output: $out" }
        return @{rc=$rc; out=$out}
    } catch {
        $report.errors += "Exception: $_"
        return @{rc=1; out=$_}
    }
}
Set-Location -Path 'C:\Users\jared\Vibe Coding (root)'
R 'git --version'
R 'git config user.name "JMCJDog"'
R 'git config user.email "jared.cohen55@gmail.com"'
if (-not (Test-Path -Path .git)) { R 'git init' }
R 'git add -A'
$st = R 'git status --porcelain'
if ($st.out -and $st.out.Trim() -ne '') { R 'git commit -m "chore: initial infra and app files"' }
$rev = R 'git rev-parse --verify main'
if ($rev.rc -ne 0) { R 'git branch -M main' }
# try gh
$gh = R 'gh --version'
$ghok = $false
$token = $env:GITHUB_TOKEN
if ($gh.rc -eq 0) {
    $auth = R 'gh auth status -h github.com'
    if ($auth.rc -eq 0) { $ghok = $true }
    elseif ($token) { R "echo $env:GITHUB_TOKEN | gh auth login --with-token"; $auth2 = R 'gh auth status -h github.com'; if ($auth2.rc -eq 0) { $ghok = $true } }
}
if ($ghok) {
    $c = R 'gh repo create JMCJDog/vibe-coding --public --source . --remote origin --push --confirm'
    if ($c.rc -eq 0) { $report.created = $true; $report.pushed = $true; $report.remote_url = 'https://github.com/JMCJDog/vibe-coding.git' }
    else { $report.errors += 'gh repo create failed' }
} else {
    if ($token) {
        try {
            $headers = @{ Authorization = "token $token"; "User-Agent" = "vibe-coding-script" }
            $body = @{ name = 'vibe-coding'; private = $false } | ConvertTo-Json
            $resp = Invoke-RestMethod -Uri 'https://api.github.com/user/repos' -Method Post -Headers $headers -Body $body -ContentType 'application/json'
            if ($resp.full_name) { $report.created = $true; $report.remote_url = "https://github.com/" + $resp.full_name + ".git" }
        } catch { $report.errors += "API error: $_" }
        if ($report.remote_url) { R "git remote add origin $($report.remote_url)"; R 'git push -u origin main'; if ($LASTEXITCODE -eq 0) { $report.pushed = $true } }
    } else {
        $report.remote_url = 'https://github.com/JMCJDog/vibe-coding.git'
        R "git remote add origin $($report.remote_url)"
        R 'git push -u origin main'
        if ($LASTEXITCODE -eq 0) { $report.pushed = $true } else { $report.errors += 'No credentials to push; manual auth required' }
    }
}
$report | ConvertTo-Json -Depth 10 | Out-File -FilePath './vibe_create_report.json' -Encoding utf8
Write-Output 'WROTE_REPORT'
