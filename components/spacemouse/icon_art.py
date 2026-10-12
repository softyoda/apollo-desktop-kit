"""Small vector-style SpaceMouse symbol, rendered at native tray/installer sizes."""
from PIL import Image, ImageDraw


def icon(color="#38bdf8", size=256):
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    d.rounded_rectangle((8, 8, 248, 248), radius=58, fill="#14243a")
    d.ellipse((47, 139, 209, 212), fill="#243e59")
    d.rounded_rectangle((64, 95, 192, 172), radius=27, fill=color)
    d.ellipse((64, 68, 192, 128), fill="#e8f4ff")
    d.ellipse((83, 78, 173, 111), fill="#c0deef")
    d.line((99, 185, 157, 185), fill="#92b9d7", width=7)
    d.ellipse((179, 177, 222, 220), fill="#14243a")
    d.ellipse((186, 184, 215, 213), fill=color)
    return image.resize((size, size), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    from pathlib import Path
    target = Path(__file__).parent / "assets"
    target.mkdir(exist_ok=True)
    icon().save(target / "spacemouse.ico", sizes=[(16,16),(20,20),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
    icon().save(target / "spacemouse.png")
