param(
    [string]$OutputPath = ".\car-plate-web-release.zip"
)

$ErrorActionPreference = "Stop"

$root = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$output = [System.IO.Path]::GetFullPath((Join-Path $root $OutputPath))
$temp = Join-Path $env:TEMP ("car-plate-web-release-" + [System.Guid]::NewGuid().ToString("N"))

$excludePatterns = @(
    "\\.git\\",
    "\\.idea\\",
    "\\.venv\\",
    "\\__pycache__\\",
    "\\frontend\\node_modules\\",
    "\\frontend\\dist\\",
    "\\backend\\mariadb-data\\",
    "\\backend\\storage\\uploads\\",
    "\\backend\\storage\\plates\\",
    "\\backend\\storage\\frames\\",
    "\\datasets\\",
    "\\runs\\",
    "\\results\\"
)

$excludeFiles = @(
    "backend\.env",
    "output.log"
)

if (Test-Path -LiteralPath $output) {
    Remove-Item -LiteralPath $output -Force
}

New-Item -ItemType Directory -Force -Path $temp | Out-Null

Get-ChildItem -LiteralPath $root -Recurse -File -Force | ForEach-Object {
    $source = $_.FullName
    $relative = $source.Substring($root.Path.Length).TrimStart("\", "/")

    $skip = $false
    foreach ($file in $excludeFiles) {
        if ($relative -ieq $file) {
            $skip = $true
            break
        }
    }
    foreach ($pattern in $excludePatterns) {
        if ($source -match $pattern) {
            $skip = $true
            break
        }
    }

    if (-not $skip) {
        $destination = Join-Path $temp $relative
        $destinationDir = Split-Path -Parent $destination
        New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $output -Force
Remove-Item -LiteralPath $temp -Recurse -Force

Write-Host "Release package created: $output"
