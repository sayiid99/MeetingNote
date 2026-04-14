[CmdletBinding()]
param(
    [string]$ProjectRoot = "",
    [string]$OutputDir = "",
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $ProjectRoot = (Resolve-Path $ProjectRoot).Path
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $ProjectRoot "dist"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stagingRoot = Join-Path $OutputDir "staging_$timestamp"
$packageRoot = Join-Path $stagingRoot "MeetingNote"
$zipPath = Join-Path $OutputDir "MeetingNote-github-$timestamp.zip"

if (Test-Path $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null

$excludeTopDirs = @(
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    "data",
    "models"
)

$excludeNameDirs = @(
    "__pycache__"
)

$excludeFilePatterns = @(
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.sqlite",
    "*.sqlite3",
    "*.db"
)

function Copy-FilteredTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$DestinationPath,
        [string]$RelativePath = ""
    )

    foreach ($item in Get-ChildItem -LiteralPath $SourcePath -Force) {
        $childRelative = if ([string]::IsNullOrWhiteSpace($RelativePath)) {
            $item.Name
        } else {
            Join-Path $RelativePath $item.Name
        }
        $childRelativeNorm = ($childRelative -replace "\\", "/")

        if ($item.PSIsContainer) {
            if ([string]::IsNullOrWhiteSpace($RelativePath) -and ($excludeTopDirs -contains $item.Name)) {
                continue
            }
            if ($excludeNameDirs -contains $item.Name) {
                continue
            }
            if ($item.Name -like "*.egg-info") {
                continue
            }
            if ($childRelativeNorm -eq "tools/ffmpeg" -or $childRelativeNorm.StartsWith("tools/ffmpeg/")) {
                continue
            }

            $destDir = Join-Path $DestinationPath $item.Name
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            Copy-FilteredTree -SourcePath $item.FullName -DestinationPath $destDir -RelativePath $childRelative
            continue
        }

        $skipFile = $false
        foreach ($pattern in $excludeFilePatterns) {
            if ($item.Name -like $pattern) {
                $skipFile = $true
                break
            }
        }
        if ($skipFile) {
            continue
        }

        Copy-Item -LiteralPath $item.FullName -Destination (Join-Path $DestinationPath $item.Name) -Force
    }
}

Copy-FilteredTree -SourcePath $ProjectRoot -DestinationPath $packageRoot

$placeholderFiles = @(
    "data/.gitkeep",
    "models/.gitkeep",
    "tools/ffmpeg/bin/.gitkeep"
)

foreach ($placeholder in $placeholderFiles) {
    $placeholderPath = Join-Path $packageRoot $placeholder
    $placeholderDir = Split-Path -Parent $placeholderPath
    New-Item -ItemType Directory -Path $placeholderDir -Force | Out-Null
    if (-not (Test-Path $placeholderPath)) {
        New-Item -ItemType File -Path $placeholderPath -Force | Out-Null
    }
}

if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

Compress-Archive -Path $packageRoot -DestinationPath $zipPath -CompressionLevel Optimal

if (-not $KeepStaging) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}

Write-Host "[OK] GitHub upload package created:"
Write-Host "     $zipPath"
if ($KeepStaging) {
    Write-Host "[INFO] Staging folder kept:"
    Write-Host "       $stagingRoot"
}
