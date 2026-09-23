import os
from PIL import Image, ImageDraw, ImageFont

def draw_sci_fi_icon():
    # Create transparent image
    img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    
    # Draw outer glowing rings
    for i in range(1, 15):
        alpha = int(255 - (i * 15))
        if alpha < 0: alpha = 0
        d.ellipse((10+i, 10+i, 246-i, 246-i), outline=(0, 229, 255, alpha), width=3)
        
    # Inner tech circle
    d.ellipse((40, 40, 216, 216), fill=(5, 14, 20, 255), outline=(0, 255, 255, 255), width=4)
    
    # Try to load a tech font, or fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
        
    # Draw an "AI Core" dot
    d.ellipse((108, 108, 148, 148), fill=(0, 255, 255, 255))
    
    # Save as ICO
    icon_path = os.path.abspath('jarvis_icon.ico')
    img.save(icon_path, format='ICO', sizes=[(256, 256)])
    print(f"[+] Created {icon_path}")
    
    # Update shortcut
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut_path = os.path.join(desktop, 'J.A.R.V.I.S.lnk')
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.IconLocation = icon_path
        # Use pythonw in a batch script to hide console? Actually, changing the target to a vbs script hides it completely.
        shortcut.save()
        print("[+] Updated desktop shortcut icon!")
    except Exception as e:
        print(f"[!] Error updating shortcut: {e}")

if __name__ == "__main__":
    draw_sci_fi_icon()
