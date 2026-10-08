@@ -0,0 +1,8 @@
@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo The project Python environment is missing. Follow the setup steps in README.md.
  pause
  exit /b 1
)
powershell.exe -NoProfile -Command "$taskStatus = $null; try { $taskStatus = Invoke-RestMethod 'http://127.0.0.1:8766/api/status' -TimeoutSec 2 } catch {}; if ($taskStatus.application -ne 'FuelScope') { Start-Process -FilePath '.venv\Scripts\python.exe' -ArgumentList '-m scripts.serve_review --port 8766' -WorkingDirectory (Get-Location).Path -WindowStyle Hidden; Start-Sleep -Seconds 2 }; Start-Process 'http://127.0.0.1:8766/'"