from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"D:\Leverage\artifacts\p001")
OUT.mkdir(parents=True, exist_ok=True)

BG = (244, 241, 234)
PAPER = (255, 253, 248)
INK = (21, 21, 21)
MUTED = (106, 103, 95)
ACCENT = (213, 106, 40)
LINE = (216, 209, 197)
GREEN = (46, 125, 79)


def font(size, bold=False):
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded(draw, xy, radius=22, fill=PAPER, outline=LINE, width=2):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def cover():
    W, H = 1600, 900
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 10), fill=ACCENT)
    d.text((90, 78), "LEVERAGE", font=font(28, True), fill=INK)
    d.text((90, 135), "FABRICATION • WELDING • JOB SHOP", font=font(18, True), fill=MUTED)
    d.multiline_text((90, 195), "Quote the job.\nSee the margin.\nProtect the profit.", font=font(72, True), fill=INK, spacing=4)
    d.text((94, 455), "Fabrication Shop Profit & Quote System", font=font(32, True), fill=ACCENT)
    d.text((94, 505), "Macro-free Excel workflow for shop rates, quoting, job costing\nand quoted-vs-actual profit review.", font=font(23), fill=MUTED, spacing=6)

    rounded(d, (900, 110, 1510, 770), radius=28)
    d.rectangle((930, 150, 1480, 215), fill=(236, 232, 223))
    d.text((958, 173), "QUOTE BUILDER", font=font(16, True), fill=MUTED)
    d.text((1350, 173), "DRAFT", font=font(15, True), fill=GREEN)
    d.text((955, 250), "Fabrication Shop Profit & Quote System", font=font(24, True), fill=INK)
    cols = ["CATEGORY", "DESCRIPTION", "QTY", "RATE", "LINE COST", "SELL"]
    xs = [955, 1070, 1300, 1360, 1430, 0]
    for i, text in enumerate(cols[:-1]):
        d.text((xs[i], 300), text, font=font(11, True), fill=MUTED)
    rows = [
        ("Material", "Mild steel plate", "8", "RM 42", "RM 336", "RM 386"),
        ("Labour", "Cut + weld", "6", "RM 70", "RM 420", "RM 420"),
        ("Consumable", "Wire + gas", "1", "RM 85", "RM 85", "RM 94"),
    ]
    y = 345
    for row in rows:
        d.line((955, y-12, 1460, y-12), fill=LINE, width=1)
        d.text((955, y), row[0], font=font(13, True), fill=INK)
        d.text((1070, y), row[1], font=font(13), fill=MUTED)
        d.text((1300, y), row[2], font=font(13), fill=INK)
        d.text((1360, y), row[3], font=font(13), fill=INK)
        d.text((1430, y), row[4], font=font(13), fill=INK)
        y += 72
    d.line((955, 575, 1460, 575), fill=LINE, width=2)
    d.text((955, 610), "TARGET QUOTE", font=font(14, True), fill=MUTED)
    d.text((1290, 600), "RM 1,150", font=font(34, True), fill=INK)
    d.text((955, 680), "GROSS PROFIT", font=font(12, True), fill=MUTED)
    d.text((1110, 674), "RM 210", font=font(21, True), fill=GREEN)
    d.text((1250, 680), "MARGIN 18.3%", font=font(12, True), fill=MUTED)
    d.text((1390, 674), "CHECKED", font=font(14, True), fill=GREEN)
    im.save(OUT / "p001-cover.png", quality=95)


def thumb():
    S = 800
    im = Image.new("RGB", (S, S), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, S, 8), fill=ACCENT)
    d.text((52, 55), "LEVERAGE", font=font(24, True), fill=INK)
    d.text((52, 108), "FABRICATION SHOP", font=font(13, True), fill=MUTED)
    d.multiline_text((52, 150), "PROFIT\n& QUOTE\nSYSTEM", font=font(62, True), fill=INK, spacing=-2)
    rounded(d, (420, 100, 748, 700), radius=24)
    d.text((450, 135), "QUOTE BUILDER", font=font(13, True), fill=MUTED)
    d.text((450, 185), "RM 1,150", font=font(34, True), fill=INK)
    d.text((450, 245), "TARGET QUOTE", font=font(11, True), fill=MUTED)
    d.line((450, 300, 715, 300), fill=LINE, width=2)
    metrics = [("COST", "RM 940"), ("PROFIT", "RM 210"), ("MARGIN", "18.3%")]
    y = 340
    for label, val in metrics:
        d.text((450, y), label, font=font(11, True), fill=MUTED)
        d.text((450, y+30), val, font=font(24, True), fill=GREEN if label != "COST" else INK)
        y += 95
    d.text((52, 690), "Macro-free Excel · shop rates · job costing", font=font(17, True), fill=ACCENT)
    im.save(OUT / "p001-thumbnail.png", quality=95)


if __name__ == "__main__":
    cover()
    thumb()
    print(OUT / "p001-cover.png")
    print(OUT / "p001-thumbnail.png")
