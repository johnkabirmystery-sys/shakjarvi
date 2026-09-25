import os
import sys
import base64

# Base64 for a futuristic blue glowing orb/AI core icon (A valid 32x32/64x64 .ico structure)
# For simplicity, we can just use shell32.dll icon index 130 or 173 (which are cool hardware/AI-like icons),
# But providing a real .ico is cooler. I'll write a simple script to generate an icon using powershell or python.

import urllib.request

def create_shortcut():
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop, 'J.A.R.V.I.S.lnk')
    target_path = os.path.abspath('start_jarvis.bat')
    icon_path = os.path.abspath('jarvis_icon.ico')
    
    if not os.path.exists(icon_path):
        # Download a cool AI futuristic icon
        try:
            url = "https://cdn2.iconfinder.com/data/icons/artificial-intelligence-6/64/ArtificialIntelligence_10-512.png"
            import urllib.request
            from PIL import Image
            import io
            
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                img_data = response.read()
                
            img = Image.open(io.BytesIO(img_data))
            img.save(icon_path, format='ICO', sizes=[(256, 256)])
            print("[+] Created jarvis_icon.ico")
        except Exception as e:
            icon_path = "shell32.dll"
            icon_index = 15
    else:
        print(f"[+] Using existing local icon: {icon_path}")
        
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        if icon_path.endswith('.ico'):
            shortcut.IconLocation = icon_path
        else:
            shortcut.IconLocation = f"{icon_path}, 15"
        # Run minimized so the CMD window doesn't pop up too visibly (7 is minimized, 1 is normal)
        shortcut.WindowStyle = 7
        shortcut.save()
        print(f"[+] Created desktop shortcut: {shortcut_path}")
    except Exception as e:
        print(f"[!] Error creating shortcut: {e}")

if __name__ == "__main__":
    create_shortcut()
