"""Cut and join the pitch clips (from record-pitch.mjs) into one 1920x1080 H.264 video, in script order.

Desktop segments fill the frame; phone segments sit in a drawn phone frame on a NEXUS panel with a one-line caption.
Usage: python scripts/compose-pitch.py <outDir> <output.mp4>
Needs ffmpeg with libx264 (imageio-ffmpeg provides one) and Pillow.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT, TARGET = Path(sys.argv[1]), Path(sys.argv[2])
W, H, FPS, FADE = 1920, 1080, 30, 0.25
ORDER = ["1-home-dashboard", "2-competency", "3-learning-path", "4-ai-tutor", "5-material-to-mcq", "6-dashboard-progress"]
CAPTIONS = {  # phone segments only; the speaker covers the rest
    "3-learning-path": ("Personalised learning path", "iGOT Karmayogi & NSSTA courses from a sample catalogue, ordered by skill gap"),
    "5-material-to-mcq": ("Quiz from uploaded material", "Practice questions written by AI from the officer's own notes, with the source passage"),
}
ASSETS = Path(__file__).resolve().parent.parent / "public" / "assets" / "generated"


def ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return "ffmpeg"


def font(size: int, bold: bool = False):
    for name in (["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
        except OSError:
            continue
    return ImageFont.load_default()


def gradient() -> Image.Image:
    img = Image.new("RGB", (W, H))
    top, bottom = (247, 250, 254), (214, 232, 255)
    for y in range(H):
        t = y / (H - 1)
        ImageDraw.Draw(img).line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


# Phone geometry: the screen keeps the 390x844 aspect ratio.
SCREEN_H = 960
SCREEN_W = round(SCREEN_H * 390 / 844)
BEZEL, RADIUS = 16, 54
PHONE_X = 1010
SX, SY = PHONE_X + BEZEL, (H - SCREEN_H) // 2


def phone_layers(seg: str, work: Path) -> tuple[Path, Path]:
    """(background under the video, bezel over it with a rounded screen hole)."""
    bg = gradient()
    d = ImageDraw.Draw(bg)
    try:
        mark = Image.open(ASSETS / "nexus-wordmark.png").convert("RGBA")
        mark.thumbnail((300, 80))
        bg.paste(mark, (170, 300), mark)
    except FileNotFoundError:
        d.text((170, 300), "NEXUS", font=font(64, True), fill=(11, 42, 91))
    chip = d.textlength("Mobile view", font=font(24, True))
    d.rounded_rectangle((170, 420, 170 + chip + 44, 462), 21, fill=(20, 100, 232))
    d.text((192, 425), "Mobile view", font=font(24, True), fill="white")
    title, sub = CAPTIONS[seg]
    d.text((170, 500), title, font=font(52, True), fill=(11, 42, 91))
    words, line, y = sub.split(), "", 585
    for w in words:                                   # wrap the subtitle to ~620 px
        test = f"{line} {w}".strip()
        if d.textlength(test, font=font(30)) > 640:
            d.text((170, y), line, font=font(30), fill=(51, 71, 106)); y += 44; line = w
        else:
            line = test
    d.text((170, y), line, font=font(30), fill=(51, 71, 106))
    # phone shadow + body under the video
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((PHONE_X + 18, SY - BEZEL + 26, PHONE_X + SCREEN_W + 2 * BEZEL + 18, SY + SCREEN_H + BEZEL + 26),
                                             RADIUS + BEZEL, fill=(11, 42, 91, 60))
    bg = Image.alpha_composite(bg.convert("RGBA"), shadow)
    under = work / f"{seg}-under.png"
    bg.convert("RGB").save(under)
    # bezel over the video: dark body, transparent rounded screen
    over = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(over)
    od.rounded_rectangle((PHONE_X, SY - BEZEL, PHONE_X + SCREEN_W + 2 * BEZEL, SY + SCREEN_H + BEZEL), RADIUS + BEZEL, fill=(16, 24, 40, 255))
    hole = Image.new("L", (W, H), 0)
    ImageDraw.Draw(hole).rounded_rectangle((SX, SY, SX + SCREEN_W, SY + SCREEN_H), RADIUS, fill=255)
    over.putalpha(Image.eval(Image.composite(Image.new("L", (W, H), 0), over.getchannel("A"), hole), lambda a: a))
    ImageDraw.Draw(over).rounded_rectangle((SX + SCREEN_W // 2 - 60, SY + 10, SX + SCREEN_W // 2 + 60, SY + 36), 13, fill=(16, 24, 40, 255))  # notch
    top = work / f"{seg}-over.png"
    over.save(top)
    return under, top


def main() -> None:
    segs = {s["id"]: s for s in json.loads((OUT / "segments.json").read_text())}
    work = OUT / "parts"
    work.mkdir(exist_ok=True)
    ff, parts = ffmpeg(), []
    for i, seg in enumerate(ORDER):
        s = segs[seg]
        src = OUT / f"{s['clip']}.webm"
        layers = phone_layers(seg, work) if s["clip"] != "desktop" else None
        for k, (start, end) in enumerate(s["parts"]):            # kept intervals; page loads between them were cut out
            dur = end - start
            part = work / f"{i}-{seg}-{k}.mp4"
            if layers is None:
                vf = f"scale=-2:{H}:flags=lanczos,pad={W}:{H}:(ow-iw)/2:0:color=0xEAF4FF,fps={FPS},format=yuv420p"
                cmd = [ff, "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(src), "-vf", vf]
            else:
                under, over = layers
                fc = (f"[1:v]scale={SCREEN_W}:{SCREEN_H}:flags=lanczos,fps={FPS}[m];[0:v][m]overlay={SX}:{SY}[a];"
                      f"[a][2:v]overlay=0:0,format=yuv420p[v]")
                cmd = [ff, "-y", "-loglevel", "error", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.2f}", "-i", str(under),
                       "-ss", f"{start:.2f}", "-t", f"{dur:.2f}", "-i", str(src), "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.2f}", "-i", str(over),
                       "-filter_complex", fc, "-map", "[v]"]
            subprocess.run(cmd + ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", str(FPS), str(part)], check=True)
            parts.append((part, dur, seg))
    # join with short crossfades
    inputs, chain, offset, last = [], "", 0.0, "0:v"
    for i, (p, _, _) in enumerate(parts):
        inputs += ["-i", str(p)]
    for i in range(1, len(parts)):
        offset += parts[i - 1][1] - FADE
        label = f"x{i}"
        chain += f"[{last}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[{label}];"
        last = label
    chain = chain.rstrip(";")
    subprocess.run([ff, "-y", "-loglevel", "error", *inputs, "-filter_complex", chain, "-map", f"[{last}]",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(TARGET)], check=True)
    total = sum(d for _, d, _ in parts) - FADE * (len(parts) - 1)
    print(f"saved {TARGET} ({total:.1f} s)")
    for seg in ORDER:
        print(f"  {seg:24s} {sum(d for _, d, s in parts if s == seg) - FADE:5.1f} s")


if __name__ == "__main__":
    main()
