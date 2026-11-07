"""Dessine les icônes de l'application mobile (PWA) : monogramme « A » et balance, couleurs AMENA."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SORTIE = Path(__file__).resolve().parents[1] / "mobile" / "icones"
SORTIE.mkdir(parents=True, exist_ok=True)


def police(taille):
    for nom in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


for taille in (192, 512, 1024):
    s = taille * 4  # dessin en grand puis réduction : bords lisses
    im = Image.new("RGB", (s, s), (110, 10, 30))
    d = ImageDraw.Draw(im)
    # disque intérieur (zone sûre des icônes « maskable »)
    m = int(s * 0.12)
    d.ellipse((m, m, s - m, s - m), fill=(200, 16, 46))
    # fléau et plateaux de la balance
    c, haut = s // 2, int(s * 0.30)
    d.line((int(s * 0.28), haut, int(s * 0.72), haut), fill=(255, 227, 233), width=int(s * 0.018))
    for x in (int(s * 0.30), int(s * 0.70)):
        d.line((x, haut, x - int(s * 0.07), int(s * 0.44)), fill=(255, 227, 233), width=int(s * 0.010))
        d.line((x, haut, x + int(s * 0.07), int(s * 0.44)), fill=(255, 227, 233), width=int(s * 0.010))
        d.chord((x - int(s * 0.09), int(s * 0.40), x + int(s * 0.09), int(s * 0.50)), 0, 180, fill=(255, 159, 178))
    # monogramme
    f = police(int(s * 0.36))
    d.text((c, int(s * 0.66)), "A", font=f, fill=(255, 255, 255), anchor="mm")
    im.resize((taille, taille), Image.LANCZOS).save(SORTIE / f"icone-{taille}.png", optimize=True)
    print("icône", taille)
