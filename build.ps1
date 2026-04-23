# Stop on error
$ErrorActionPreference = "Stop"

# Output directory
$OUTPUT_DIR = "build"

# Create build folder if not exists
if (!(Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Path $OUTPUT_DIR | Out-Null
}

Write-Host "🔨 Building Proctoring Agent..." -ForegroundColor Cyan

# -------------------------
# Windows Build
# -------------------------
Write-Host "➡️ Building for Windows..." -ForegroundColor Yellow
$env:GOOS = "windows"
$env:GOARCH = "amd64"
go build -ldflags="-s -w" -o "$OUTPUT_DIR\proctoring-agent-windows-amd64.exe"

# Optional: hide console window
# go build -ldflags="-H=windowsgui -s -w" -o "$OUTPUT_DIR\proctoring-agent-windows-amd64.exe"

# -------------------------
# macOS Intel Build
# -------------------------
Write-Host "➡️ Building for macOS (Intel)..." -ForegroundColor Yellow
$env:GOOS = "darwin"
$env:GOARCH = "amd64"
go build -ldflags="-s -w" -o "$OUTPUT_DIR\proctoring-agent-mac-intel"

# -------------------------
# macOS Apple Silicon Build
# -------------------------
Write-Host "➡️ Building for macOS (Apple Silicon)..." -ForegroundColor Yellow
$env:GOOS = "darwin"
$env:GOARCH = "arm64"
go build -ldflags="-s -w" -o "$OUTPUT_DIR\proctoring-agent-mac-arm"

# -------------------------
# Reset environment
# -------------------------
Remove-Item Env:GOOS -ErrorAction SilentlyContinue
Remove-Item Env:GOARCH -ErrorAction SilentlyContinue

Write-Host "✅ Build complete! Files are in /build" -ForegroundColor Green