"""Bannière Google Play (« feature graphic ») 1024 × 500 : photo du Palais de Justice de Tunis, titre et icône."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "stores" / "banniere-play-1024x500.png"


def police(taille, gras=True):
    for nom in (("segoeuib.ttf", "arialbd.ttf") if gras else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


fond = Image.open(RACINE / "web" / "img" / "photos" / "palais-justice-tunis.webp").convert("RGB")
w, h = 1024, 500
r = max(w / fond.width, h / fond.height)
fond = fond.resize((round(fond.width * r), round(fond.height * r)), Image.LANCZOS)
fond = fond.crop(((fond.width - w) // 2, (fond.height - h) // 3, (fond.width - w) // 2 + w, (fond.height - h) // 3 + h))
# voile bordeaux, plus dense à gauche pour la lisibilité du texte
voile = Image.new("RGB", (w, h), (28, 5, 9))
masque = Image.linear_gradient("L").rotate(90).resize((w, h))
masque = masque.point(lambda v: int(70 + v * 0.6))
fond = Image.composite(voile, fond, masque)
teinte = Image.new("RGB", (w, h), (110, 10, 30))
fond = Image.blend(fond, teinte, 0.25)

d = ImageDraw.Draw(fond)
d.text((60, 120), "AMENA", font=police(108), fill=(255, 255, 255))
d.text((62, 250), "Votre avocate de poche", font=police(44), fill=(255, 159, 178))
d.text((62, 315), "Le droit tunisien expliqué à tous", font=police(30, False), fill=(240, 225, 229))
d.text((62, 358), "Français · Arabe · Derja", font=police(30, False), fill=(240, 225, 229))
icone = Image.open(RACINE / "mobile" / "icones" / "icone-512.png").resize((190, 190), Image.LANCZOS)
fond.paste(icone, (w - 250, (h - 190) // 2))
fond.save(SORTIE, optimize=True)
print(SORTIE, fond.size)
