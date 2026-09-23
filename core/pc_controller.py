import os
import time
import ctypes
import subprocess
import webbrowser
import base64
from pathlib import Path
from pycaw.pycaw import AudioUtilities

VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF

COMMON_APPS = {
    "chrome": "start chrome",
    "google chrome": "start chrome",
    "browser": "start chrome",
    "edge": "start msedge",
    "firefox": "start firefox",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "terminal": "wt.exe",
    "cmd": "start cmd.exe",
    "powershell": "start powershell.exe",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "settings": "start ms-settings:",
    "spotify": "start spotify:",
    "discord": "start discord:",
    "steam": "start steam:",
    "paint": "mspaint.exe"
}

def launch_app(app_name: str) -> dict:
    clean = app_name.strip().lower()
    if clean in COMMON_APPS:
        cmd = COMMON_APPS[clean]
        try:
            subprocess.Popen(cmd, shell=True)
            return {"success": True, "message": f"Successfully initiated {app_name}, Sir Shakil."}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    try:
        subprocess.Popen(f"start {app_name}", shell=True)
        return {"success": True, "message": f"Launching {app_name}."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def close_app(name: str) -> dict:
    target = name.strip()
    if not target.endswith(".exe"):
        target += ".exe"
    try:
        res = subprocess.run(["taskkill", "/F", "/IM", target], capture_output=True, text=True)
        if res.returncode == 0:
            return {"success": True, "message": f"Terminated {target} as instructed, Sir Shakil."}
        return {"success": False, "message": f"Could not find or terminate {target}: {res.stderr.strip()}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def get_volume_endpoint():
    try:
        speakers = AudioUtilities.GetSpeakers()
        return getattr(speakers, "EndpointVolume", None)
    except Exception:
        return None

def get_volume() -> dict:
    try:
        endpoint = get_volume_endpoint()
        if endpoint:
            level = round(endpoint.GetMasterVolumeLevelScalar() * 100)
            is_muted = bool(endpoint.GetMute())
            return {"level": level, "is_muted": is_muted}
        return {"level": 50, "is_muted": False}
    except Exception as e:
        return {"error": str(e), "level": 50, "is_muted": False}

def set_volume(percent: int) -> dict:
    try:
        percent = max(0, min(100, int(percent)))
        endpoint = get_volume_endpoint()
        if endpoint:
            endpoint.SetMasterVolumeLevelScalar(percent / 100.0, None)
            if endpoint.GetMute():
                endpoint.SetMute(0, None)
            return {"success": True, "level": percent, "message": f"Master audio calibrated to {percent}%, Sir Shakil."}
        return {"success": False, "error": "Audio device unreachable"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def mute_volume(mute_state=None) -> dict:
    try:
        endpoint = get_volume_endpoint()
        if endpoint:
            current = bool(endpoint.GetMute())
            new_state = (not current) if mute_state is None else bool(mute_state)
            endpoint.SetMute(1 if new_state else 0, None)
            status_str = "muted" if new_state else "unmuted"
            return {"success": True, "is_muted": new_state, "message": f"Audio channels {status_str}, Sir Shakil."}
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 2, 0)
        return {"success": True, "is_muted": None, "message": "Audio mute toggled."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def media_control(action: str) -> dict:
    action = action.lower().strip()
    user32 = ctypes.windll.user32
    key_map = {
        "play": VK_MEDIA_PLAY_PAUSE,
        "pause": VK_MEDIA_PLAY_PAUSE,
        "play_pause": VK_MEDIA_PLAY_PAUSE,
        "next": VK_MEDIA_NEXT_TRACK,
        "prev": VK_MEDIA_PREV_TRACK,
        "previous": VK_MEDIA_PREV_TRACK,
        "stop": VK_MEDIA_STOP
    }
    if action in key_map:
        vk = key_map[action]
        user32.keybd_event(vk, 0, 0, 0)
        user32.keybd_event(vk, 0, 2, 0)
        return {"success": True, "message": f"Media command '{action}' triggered."}
    return {"success": False, "error": f"Unknown media action '{action}'"}

def lock_workstation() -> dict:
    try:
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "Workstation secured. Protocols locked down, Sir Shakil."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def open_url(url: str) -> dict:
    try:
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "https://" + url
        webbrowser.open(url)
        return {"success": True, "message": f"Opened link: {url}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def search_web(query: str) -> dict:
    try:
        url = f"https://www.google.com/search?q={query}"
        webbrowser.open(url)
        return {"success": True, "message": f"Querying planetary information index for '{query}', Sir Shakil."}
    except Exception as e:
        return {"success": False, "error": str(e)}

def take_screenshot(filename: str = None) -> dict:
    try:
        data_dir = Path("data/screenshots")
        data_dir.mkdir(parents=True, exist_ok=True)
        if not filename:
            filename = f"capture_{int(time.time())}.png"
        filepath = data_dir / filename
        
        abs_path = str(filepath.resolve()).replace("\\", "/")
        script_path = data_dir / "grab_temp.ps1"
        ps_code = "\n".join([
            "Add-Type -AssemblyName System.Windows.Forms",
            "Add-Type -AssemblyName System.Drawing",
            "$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds",
            "$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height",
            "$g = [System.Drawing.Graphics]::FromImage($bmp)",
            "$g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)",
            "$bmp.Save('" + abs_path + "', [System.Drawing.Imaging.ImageFormat]::Png)",
            "$g.Dispose()",
            "$bmp.Dispose()"
        ])
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(ps_code)
            
        res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)], capture_output=True, text=True)
        if script_path.exists():
            script_path.unlink(missing_ok=True)
            
        if filepath.exists():
            with open(filepath, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            return {"success": True, "filepath": str(filepath), "base64": b64, "message": "Visual capture acquired and analyzed, Sir Shakil."}
        return {"success": False, "error": f"Screenshot failed: {res.stderr.strip()}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_shell(command: str, timeout: int = 20) -> dict:
    try:
        res = subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, text=True, timeout=timeout)
        return {
            "success": res.returncode == 0,
            "exit_code": res.returncode,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip()
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command execution timed out."}
    except Exception as e:
        return {"success": False, "error": str(e)}
