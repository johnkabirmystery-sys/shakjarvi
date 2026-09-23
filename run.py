import os
import sys
import time
import socket
import urllib.request
from pathlib import Path
from threading import Thread

# 1. Windows 11 Desktop Integration & Taskbar Identity
try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Shakil.Jarvis.MarkXVI.NativeOS")
except Exception:
    pass

# 2. Pre-configure WebView2 for automatic microphone and audio playback permissions
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = (
    "--use-fake-ui-for-media-stream "
    "--enable-features=HardwareMediaKeyHandling "
    "--autoplay-policy=no-user-gesture-required "
    "--disable-features=msSmartScreenProtection"
)

# Dedicated profile directory for Jarvis Desktop to avoid locking conflicts
JARVIS_USER_DATA_DIR = Path.home() / ".jarvis_desktop_profile"
JARVIS_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(JARVIS_USER_DATA_DIR)

import uvicorn

BANNER = r"""
===================================================================
      _____  ___  ______ _   _ _____ _____ 
     |_   _|/ _ \ | ___ \ | | |_   _/  ___|
       | | / /_\ \| |_/ / | | | | | \ `--. 
       | | |  _  ||    /| | | | | |  `--. \
     \ \_/ / | | || |\ \\ \_/ /_| |_/\__/ /
      \___/\_| |_/\_| \_|\___/ \___/\____/ 

       J.A.R.V.I.S. // SHAKIL'S ASSISTANT
       ==================================
       MARK XVI - NATIVE DESKTOP EDITION
===================================================================
"""

def is_port_in_use(port: int = 8000, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def clean_stale_process_on_port(port: int = 8000):
    """Reclaims port 8000 if held by an unresponsive zombie process."""
    try:
        import subprocess
        output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True, errors="replace")
        current_pid = os.getpid()
        for line in output.strip().splitlines():
            if "LISTENING" in line:
                parts = line.strip().split()
                pid = int(parts[-1])
                if pid != current_pid and pid > 0:
                    print(f"[*] Reclaiming port {port}: terminating unresponsive process {pid}...", flush=True)
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, capture_output=True)
    except Exception:
        pass

def wait_for_server(port: int = 8000, host: str = "127.0.0.1", timeout: float = 12.0) -> bool:
    """Waits until the backend server is actively responding to HTTP requests."""
    start_time = time.time()
    url = f"http://{host}:{port}/api/settings"
    while time.time() - start_time < timeout:
        if is_port_in_use(port, host):
            try:
                with urllib.request.urlopen(url, timeout=0.8) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
        time.sleep(0.15)
    return False

class JarvisDesktopApi:
    """Bidirectional Python-JavaScript Bridge for Native Windows 11 Desktop Operations."""
    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def open_created_files_folder(self):
        folder = Path.home() / "Desktop" / "Jarvis_Created_Files"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))
            return {"success": True, "path": str(folder)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_project_folder(self):
        try:
            cwd = os.getcwd()
            os.startfile(cwd)
            return {"success": True, "path": cwd}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def minimize_window(self):
        if self._window:
            self._window.minimize()
            return {"success": True}
        return {"success": False}

    def maximize_window(self):
        if self._window:
            if getattr(self, "_is_maximized", False):
                self._window.restore()
                self._is_maximized = False
            else:
                self._window.maximize()
                self._is_maximized = True
            return {"success": True, "maximized": self._is_maximized}
        return {"success": False}

    def close_window(self):
        if self._window:
            self._window.destroy()
            return {"success": True}
        os._exit(0)

    def toggle_fullscreen(self):
        if self._window:
            self._window.toggle_fullscreen()
            return {"success": True}
        return {"success": False}

    def show_notification(self, title: str, message: str):
        try:
            import subprocess
            cmd = f'''powershell -Command "[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); $n = New-Object System.Windows.Forms.NotifyIcon; $n.Icon = [System.Drawing.SystemIcons]::Information; $n.Visible = $true; $n.ShowBalloonTip(3000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)"'''
            subprocess.Popen(cmd, shell=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def emergency_cancel(self):
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            from core.conversation_controller import conversation_controller
            from core.orchestrator import orchestrator
            asyncio.create_task(conversation_controller.abort_active_turn(reason="Desktop emergency stop"))
            asyncio.create_task(orchestrator.cancel_all_active("Desktop emergency stop"))
            return {"success": True}
        else:
            try:
                req = urllib.request.Request("http://127.0.0.1:8000/api/conversation/cancel", method="POST")
                with urllib.request.urlopen(req, timeout=0.8) as resp:
                    pass
                return {"success": True}
            except Exception:
                try:
                    from core.conversation_controller import conversation_controller
                    from core.orchestrator import orchestrator
                    async def _cancel():
                        await conversation_controller.abort_active_turn(reason="Desktop emergency stop")
                        await orchestrator.cancel_all_active("Desktop emergency stop")
                    asyncio.run(_cancel())
                    return {"success": True}
                except Exception as e:
                    return {"success": False, "error": str(e)}

def start_backend():
    config = uvicorn.Config("server:app", host="127.0.0.1", port=8000, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    server.run()

def ensure_desktop_shortcut():
    """Ensures the Windows Desktop shortcut exists and points to START_JARVIS.bat with icon."""
    try:
        import win32com.client
        desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        shortcut_path = os.path.join(desktop, 'J.A.R.V.I.S.lnk')
        target_path = os.path.abspath('START_JARVIS.bat')
        icon_path = os.path.abspath('jarvis_icon.ico')
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        if os.path.exists(icon_path):
            shortcut.IconLocation = icon_path
        shortcut.WindowStyle = 7  # Minimized CMD launcher
        shortcut.save()
        print("[*] Desktop shortcut confirmed: C:\\Users\\Qbits\\Desktop\\J.A.R.V.I.S.lnk", flush=True)
    except Exception as e:
        pass

def on_closed():
    print("[*] J.A.R.V.I.S. GUI closed. Terminating background services...", flush=True)
    os._exit(0)

if __name__ == "__main__":
    print(BANNER, flush=True)

    # 0. Refresh & confirm Desktop Shortcut
    ensure_desktop_shortcut()

    # 1. Ensure port 8000 is clean and healthy
    if is_port_in_use(8000):
        # Test if it's responsive
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/api/settings", timeout=1.0) as resp:
                if resp.status == 200:
                    print("[*] Active Jarvis backend server detected on port 8000. Reusing instance.", flush=True)
                else:
                    clean_stale_process_on_port(8000)
                    time.sleep(0.5)
        except Exception:
            clean_stale_process_on_port(8000)
            time.sleep(0.5)

    # 2. Launch backend if needed
    if not is_port_in_use(8000):
        print("[*] Launching Jarvis neural backend on http://127.0.0.1:8000...", flush=True)
        server_thread = Thread(target=start_backend, daemon=True)
        server_thread.start()

    # 3. Wait for backend to be fully online and accepting HTTP requests
    ready = wait_for_server(8000, timeout=12.0)
    if ready:
        print("[*] Backend confirmed ONLINE. Initializing native holographic display...", flush=True)
    else:
        print("[!] Warning: Backend initialization timed out. Launching display anyway...", flush=True)

    # 4. Launch native desktop GUI
    api = JarvisDesktopApi()
    try:
        import webview

        window = webview.create_window(
            title="J.A.R.V.I.S. — Shakil's Personal Assistant (Mark XVI)",
            url="http://127.0.0.1:8000",
            width=1600,
            height=950,
            min_size=(1050, 680),
            resizable=True,
            fullscreen=False,
            frameless=True,
            easy_drag=True,
            shadow=True,
            confirm_close=False,
            background_color='#050e14',
            text_select=True,
            js_api=api
        )
        api.set_window(window)
        window.events.closed += on_closed

        # Start GUI event loop on main thread
        webview.start(private_mode=False, gui='edgechromium', storage_path=str(JARVIS_USER_DATA_DIR))
    except Exception as e:
        print(f"[!] PyWebView failed ({e}), opening in default browser...", flush=True)
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            os._exit(0)
