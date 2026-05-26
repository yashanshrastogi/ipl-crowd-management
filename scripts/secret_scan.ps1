param(
    [switch]$TrackedOnly
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$excludedDirectories = @(
    ".git",
    "node_modules",
    "dist",
    "build",
    ".vite",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "coverage"
)

$excludedFiles = @(
    "frontend/package-lock.json"
)

$binaryExtensions = @(
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tgz",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot"
)

$patterns = [ordered]@{
    "Google API key" = "AIza[0-9A-Za-z_-]{35}"
    "Private key block" = "-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"
    "OpenAI API key" = "\bsk-[A-Za-z0-9_-]{20,}\b"
    "GitHub token" = "\bgh[pousr]_[A-Za-z0-9_]{30,}\b"
    "AWS access key" = "\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"
    "Slack token" = "\bxox[baprs]-[A-Za-z0-9-]{10,}\b"
    "JWT" = "\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"
    "Service account private key id" = '"private_key_id"\s*:\s*"[a-f0-9]{40}"'
    "High-risk quoted secret literal" = "(?i)\b(client_secret|private_key|refresh_token|admin_api_key|api_key|password|secret|token)\b\s*[:=]\s*['""][^'""]{24,}['""]"
    "High-risk env secret value" = "^\s*[A-Z0-9_]*(CLIENT_SECRET|PRIVATE_KEY|REFRESH_TOKEN|ADMIN_API_KEY|API_KEY|PASSWORD|SECRET|TOKEN)[A-Z0-9_]*\s*=\s*[A-Za-z0-9_./+=-]{24,}\s*$"
}

function Convert-ToRelativePath {
    param([string]$Path)
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    return [System.IO.Path]::GetRelativePath($RepoRoot, $fullPath).Replace("\", "/")
}

function Test-SkippedPath {
    param([string]$RelativePath)

    if ($excludedFiles -contains $RelativePath) {
        return $true
    }

    $extension = [System.IO.Path]::GetExtension($RelativePath).ToLowerInvariant()
    if ($binaryExtensions -contains $extension) {
        return $true
    }

    $parts = $RelativePath -split "/"
    foreach ($part in $parts) {
        if ($excludedDirectories -contains $part) {
            return $true
        }
    }

    return $false
}

function Get-CandidateFiles {
    if ((Get-Command git -ErrorAction SilentlyContinue) -and (Test-Path ".git")) {
        $modeArgs = if ($TrackedOnly) { @("--cached") } else { @("--cached", "--others", "--exclude-standard") }
        return (& git ls-files @modeArgs) |
            Where-Object { $_ -and -not (Test-SkippedPath $_) } |
            Sort-Object -Unique
    }

    return Get-ChildItem -Recurse -File -Force |
        ForEach-Object { Convert-ToRelativePath $_.FullName } |
        Where-Object { $_ -and -not (Test-SkippedPath $_) } |
        Sort-Object -Unique
}

$findings = New-Object System.Collections.Generic.List[object]

foreach ($file in Get-CandidateFiles) {
    $lineNumber = 0
    try {
        Get-Content -LiteralPath $file -ErrorAction Stop | ForEach-Object {
            $lineNumber += 1
            $line = $_
            foreach ($patternName in $patterns.Keys) {
                if ($line -cmatch $patterns[$patternName]) {
                    $findings.Add([pscustomobject]@{
                        File = $file
                        Line = $lineNumber
                        Type = $patternName
                    })
                }
            }
        }
    }
    catch {
        Write-Warning "Skipped unreadable file: $file"
    }
}

if ($findings.Count -gt 0) {
    Write-Host "Potential secrets found:" -ForegroundColor Red
    $findings | Format-Table -AutoSize
    exit 1
}

Write-Host "Secret scan passed. No high-confidence secret patterns found." -ForegroundColor Green
