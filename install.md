✅ Complete Packaging Solution
Files created/modified:
File	What it does

app_server.py
New — Unified entry-point: runs FastAPI backend + serves compiled React UI from one process

DUBGG.spec
New — PyInstaller recipe with all hidden imports, frontend_dist/, and utils/ bundled

build_installer.ps1
New — One-click PowerShell script that does everything: installs deps → builds React → packages EXE

vite.config.ts
Updated — Added base: '/' and explicit outDir: 'dist' for consistent builds

src/utils/api.ts
Updated — API URL auto-detects: uses localhost:8000 in dev, relative URL in the packaged EXE
🚀 How to Build
Open PowerShell in your project folder and run just one command:

powershell
# First time (may need to allow scripts)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Build everything
.\build_installer.ps1
This will:

Install all Python packages (FastAPI, uvicorn, pymodbus, PyInstaller…)
Run npm install + npm run build for the React frontend
Package everything into dist\DUBGG_HMI.exe (~80–150 MB)
📦 How to Deploy
The target machine needs zero Python/Node/npm installed.

Copy dist\DUBGG_HMI.exe to the target Windows PC
Double-click it — a console window appears with logs
The browser opens automatically at http://127.0.0.1:8000 showing the full HMI (this avoids firewall prompts on restricted accounts).
TIP

If Windows SmartScreen blocks it, click More info -> Run anyway. Or run Unblock-File DUBGG_HMI.exe in PowerShell.

How to deploy on another machine
1. Copy dist\DUBGG_HMI.exe to the target Windows PC - that's the only file needed.
2. Double-click it.
3. A console window opens showing the server logs.
4. Default browser opens automatically at http://127.0.0.1:8000.

Note for Restricted Users:
The EXE now binds to 127.0.0.1 (localhost) by default. This avoids the Windows Firewall popup that requires admin rights. If you need other computers on the LAN to see the HMI, you must run it with:
.\DUBGG_HMI.exe --host 0.0.0.0
(This will trigger the firewall prompt).
For future rebuilds (even faster)
powershell
# Code changed on both sides
.\build_installer.ps1
# Only Python backend changed
.\build_installer.ps1 -SkipNpm
# Only React frontend changed  
.\build_installer.ps1 -SkipPipInstall
# Fastest - skip all installs (just rebuild + repackage)
.\build_installer.ps1 -SkipNpm -SkipPipInstall
Note: If Windows SmartScreen warns about the EXE on the target machine, click More info → Run anyway, or run Unblock-File DUBGG_HMI.exe in PowerShell to whitelist it.