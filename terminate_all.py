import os
import signal
import psutil
import time

def terminate_processes():
    print("Stopping DUBGG project processes (Python-based cleanup)...")
    
    # Target ports
    target_ports = [8000, 5173, 502, 5020]
    
    # Target script/process names
    target_names = ["api_server.py", "app_server.py", "generator_sim.py", "vite"]

    processed_pids = set()

    # 1. Kill by Port
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port in target_ports:
                    print(f"Killing process {proc.info['pid']} ({proc.info['name']}) listening on port {conn.laddr.port}")
                    # Use SIGKILL on Linux/Unix for faster termination, 
                    # SIGTERM on Windows (as SIGKILL is not defined or same as terminate)
                    if os.name == 'nt':
                        proc.kill()
                    else:
                        proc.send_signal(signal.SIGKILL)
                    processed_pids.add(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # 2. Kill by Name
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['pid'] in processed_pids:
                continue
                
            cmdline_list = proc.info.get('cmdline') or []
            cmdline = " ".join(cmdline_list)
            name = proc.info.get('name') or ""
            
            if any(target in cmdline or target in name for target in target_names):
                print(f"Killing process {proc.info['pid']} ({name}) based on name/cmdline matching '{target_names}'")
                if os.name == 'nt':
                    proc.kill()
                else:
                    proc.send_signal(signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    print("Cleanup complete. Waiting a moment for processes to exit...")
    time.sleep(1)

if __name__ == "__main__":
    terminate_processes()
