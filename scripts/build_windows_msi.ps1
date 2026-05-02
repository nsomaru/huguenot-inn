$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$Version = python -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['version'])"
$AppName = "Huguenot Inn"
$AppDir = Join-Path $ProjectRoot "dist\Huguenot Inn"
$MsiPath = Join-Path $ProjectRoot "dist\Huguenot-Inn-$Version-Windows-x64.msi"
$WxsPath = Join-Path $ProjectRoot "packaging\windows\huguenot-inn.wxs"

Remove-Item -Recurse -Force "build\huguenot-inn-windows", "dist\Huguenot Inn", $MsiPath -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force "dist" | Out-Null

pyinstaller --noconfirm --clean --onedir --windowed --name $AppName `
  --paths src `
  --collect-data tkinterdnd2 `
  --collect-data huguenot.persistence `
  --copy-metadata yoyo-migrations `
  --hidden-import yoyo.backends.core.sqlite3 `
  --collect-submodules docx2pdf `
  packaging\pyinstaller_entry.py

if (!(Test-Path $AppDir)) {
  throw "PyInstaller did not create $AppDir"
}

wix build $WxsPath -arch x64 -d Version=$Version -d SourceDir=$AppDir -out $MsiPath

if (!(Test-Path $MsiPath) -or ((Get-Item $MsiPath).Length -eq 0)) {
  throw "MSI was not created or is empty: $MsiPath"
}

Write-Host "Created $MsiPath"
