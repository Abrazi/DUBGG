#!/usr/bin/env python3
"""
build_app.py - Unified cross-platform build script.
Run this script to build the frontend and package the backend.

On Windows, it generates: dist/DUBGG_HMI.exe
On Linux, it generates: dist/DUBGG_HMI (Standalone ELF executable)
    AND it attempts to package an .AppImage if possible.

Usage:
    python build_app.py [--skip-npm] [--skip-pip] [--clean]
"""

import os
import sys
import subprocess
import shutil
import platform
import urllib.request
import stat

def print_header(msg):
    print(f"\n{'='*70}\n  {msg}\n{'='*70}")

def print_step(msg):
    print(f"\n[STEP] {msg}")

def print_ok(msg):
    print(f"[OK]   {msg}")

def print_err(msg):
    print(f"[ERR]  {msg}")
    sys.exit(1)

def run_cmd(cmd, **kwargs):
    try:
        subprocess.check_call(cmd, **kwargs)
    except subprocess.CalledProcessError as e:
        print_err(f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
    except FileNotFoundError:
        print_err(f"Command not found: {cmd[0]}")

def check_command(cmd_name):
    path = shutil.which(cmd_name)
    if not path:
        print_err(f"Prerequisite '{cmd_name}' not found on PATH. Please install it.")
    return path

def build_appimage():
    """Packages the PyInstaller Linux ELF into an AppImage."""
    print_step("Packaging as AppImage (Linux)...")
    
    dist_dir = os.path.join(os.getcwd(), "dist")
    linux_exe = os.path.join(dist_dir, "DUBGG_HMI")
    
    if not os.path.isfile(linux_exe):
        print_err(f"Expected PyInstaller output not found at: {linux_exe}")

    appdir = os.path.join(os.getcwd(), "AppDir")
    if os.path.isdir(appdir):
        shutil.rmtree(appdir)
        
    os.makedirs(os.path.join(appdir, "usr", "bin"))
    
    # Copy the PyInstaller executable into the AppDir
    shutil.copy2(linux_exe, os.path.join(appdir, "usr", "bin", "DUBGG_HMI"))
    
    # Create AppRun script
    apprun_path = os.path.join(appdir, "AppRun")
    with open(apprun_path, "w") as f:
        f.write("#!/bin/sh\n")
        f.write('HERE="$(dirname "$(readlink -f "${0}")")"\n')
        f.write('exec "${HERE}/usr/bin/DUBGG_HMI" "$@"\n')
    os.chmod(apprun_path, 0o755)

    # Create .desktop file
    desktop_path = os.path.join(appdir, "dubgg_hmi.desktop")
    with open(desktop_path, "w") as f:
        f.write("[Desktop Entry]\n")
        f.write("Type=Application\n")
        f.write("Name=DUBGG HMI\n")
        f.write("Exec=DUBGG_HMI\n")
        f.write("Icon=DUBGG_HMI\n")
        f.write("Categories=Utility;\n")
        f.write("Terminal=true\n") # Set to true so logs are visible
        
    # Create a dummy icon if one doesn't exist (AppImageKit requires an icon)
    icon_path = os.path.join(appdir, "DUBGG_HMI.png")
    with open(icon_path, "wb") as f:
        # A tiny valid 1x1 transparent PNG file
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

    # Download appimagetool if not exists
    appimagetool_path = os.path.join(os.getcwd(), "appimagetool-x86_64.AppImage")
    if not os.path.exists(appimagetool_path):
        print("Downloading appimagetool...")
        url = "https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage"
        try:
            urllib.request.urlretrieve(url, appimagetool_path)
            os.chmod(appimagetool_path, 0o755)
        except Exception as e:
            print(f"Warning: Failed to download appimagetool ({e}). Cannot create AppImage.")
            return

    # Run appimagetool
    print("Running appimagetool...")
    try:
        # Some linux systems require APPIMAGE_EXTRACT_AND_RUN=1 for appimagetool inside docker/CI
        env = os.environ.copy()
        env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
        subprocess.check_call([appimagetool_path, appdir, os.path.join(dist_dir, "DUBGG_HMI-x86_64.AppImage")], env=env)
        print_ok(f"AppImage created at: {os.path.join(dist_dir, 'DUBGG_HMI-x86_64.AppImage')}")
    except subprocess.CalledProcessError as e:
        print_err("appimagetool failed. See output above.")


def main():
    skip_npm = '--skip-npm' in sys.argv
    skip_pip = '--skip-pip' in sys.argv
    clean = '--clean' in sys.argv
    
    is_windows = platform.system().lower() == "windows"
    
    print_header("DUBGG Generator HMI - Unified Build Script")
    print(f"  OS: {platform.system()}")
    
    # 0. Prerequisites
    print_step("Checking prerequisites...")
    npm_cmd = "npm.cmd" if is_windows else "npm"
    check_command("node")
    check_command(npm_cmd)
    
    py_exe = sys.executable
    print_ok(f"Using Python: {py_exe}")
    
    # 1. Clean
    if clean:
        print_step("Cleaning previous build artefacts...")
        for dirname in ["dist", "build", "frontend_dist", "AppDir"]:
            if os.path.isdir(dirname):
                shutil.rmtree(dirname)
                print_ok(f"Deleted {dirname}/")
                
    # 2. Pip packages
    if not skip_pip:
        print_step("Installing Python dependencies...")
        packages = [
            "fastapi", "uvicorn[standard]", "pydantic", "pymodbus", "psutil", 
            "aiofiles", "python-multipart", "h11", "httptools", "websockets", "pyinstaller"
        ]
        run_cmd([py_exe, "-m", "pip", "install", "--quiet", "--upgrade"] + packages)
        print_ok("Python dependencies installed.")
    else:
        print_ok("Skipping pip install.")
        
    # 3. Npm packages
    if not skip_npm:
        print_step("Installing Node.js packages...")
        run_cmd([npm_cmd, "install", "--silent"])
        print_ok("Node.js packages installed.")
    else:
        print_ok("Skipping npm install.")
        
    # 4. Build Frontend
    print_step("Building React frontend...")
    run_cmd([npm_cmd, "run", "build"])
    
    if os.path.isdir("frontend_dist"):
        shutil.rmtree("frontend_dist")
    
    if os.path.isdir("dist"):
        os.rename("dist", "frontend_dist")
    else:
        print_err("Expected 'dist' output directory from 'npm run build' not found.")
        
    if not os.path.exists(os.path.join("frontend_dist", "index.html")):
        print_err("frontend_dist/index.html not found! Check Vite config.")
        
    print_ok("Frontend built successfully -> frontend_dist/")
    
    # 5. Package backend + frontend into EXE/ELF
    print_step("Packaging with PyInstaller...")
    run_cmd([py_exe, "-m", "PyInstaller", "DUBGG.spec", "--noconfirm"])
    
    if is_windows:
        exe_path = os.path.join("dist", "DUBGG_HMI.exe")
        if not os.path.exists(exe_path):
            print_err(f"Expected PyInstaller output not found at: {exe_path}")
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print_ok(f"EXE built successfully: {exe_path} ({size_mb:.1f} MB)")
        
        print_header("Build Successful!")
        print("You can find your standalone executable at:")
        print(f"  --> {os.path.abspath(exe_path)}")
        
    else:
        # Linux / MacOS
        elf_path = os.path.join("dist", "DUBGG_HMI")
        if not os.path.exists(elf_path):
            print_err(f"Expected PyInstaller output not found at: {elf_path}")
        size_mb = os.path.getsize(elf_path) / (1024 * 1024)
        print_ok(f"Standalone Linux Executable built: {elf_path} ({size_mb:.1f} MB)")
        
        # Try AppImage
        build_appimage()
        
        print_header("Build Successful!")
        print("You can find your standalone executable / AppImage at:")
        print(f"  --> {os.path.abspath('dist')}/")

if __name__ == "__main__":
    main()
