"""Visuel LinkedIn 1200 × 1500 : trois écrans de l'application dans des cadres de téléphone, sur fond AMENA."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RACINE = Path(__file__).resolve().parents[1]
DOSSIER = RACINE / "docs" / "linkedin"
W, H = 1200, 1500


def police(taille, gras=True):
    for nom in (("segoeuib.ttf", "arialbd.ttf") if gras else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(nom, taille)
        except OSError:
            continue
    return ImageFont.load_default()


def telephone(capture, largeur):
    """Capture dans un cadre de téléphone arrondi, avec ombre portée."""
    ecran = Image.open(capture).convert("RGB")
    hauteur = round(largeur * ecran.height / ecran.width)
    ecran = ecran.resize((largeur, hauteur), Image.LANCZOS)
    bord, rayon = 14, 46
    cadre = Image.new("RGBA", (largeur + 2 * bord, hauteur + 2 * bord), (0, 0, 0, 0))
    d = ImageDraw.Draw(cadre)
    d.rounded_rectangle((0, 0, cadre.width - 1, cadre.height - 1), radius=rayon + bord, fill=(12, 2, 4, 255))
    masque = Image.new("L", ecran.size, 0)
    ImageDraw.Draw(masque).rounded_rectangle((0, 0, largeur - 1, hauteur - 1), radius=rayon, fill=255)
    cadre.paste(ecran, (bord, bord), masque)
    ombre = Image.new("RGBA", (cadre.width + 80, cadre.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(ombre).rounded_rectangle((40, 60, cadre.width + 40, cadre.height + 60), radius=rayon + bord, fill=(0, 0, 0, 150))
    ombre = ombre.filter(ImageFilter.GaussianBlur(26))
    ombre.alpha_composite(cadre, (40, 40))
    return ombre


fond = Image.new("RGB", (W, H), (28, 5, 9))
degrade = Image.linear_gradient("L").resize((W, H))
fond = Image.composite(Image.new("RGB", (W, H), (110, 10, 30)), fond, degrade)
halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(halo).ellipse((W - 760, -260, W + 260, 760), fill=(200, 16, 46, 120))
fond = Image.alpha_composite(fond.convert("RGBA"), halo.filter(ImageFilter.GaussianBlur(120)))

d = ImageDraw.Draw(fond)
d.text((70, 70), "AMENA", font=police(96), fill=(255, 255, 255))
d.text((74, 190), "Votre avocate de poche", font=police(44), fill=(255, 159, 178))
d.text((74, 255), "Le droit tunisien expliqué à tous · français, arabe, derja", font=police(30, False), fill=(240, 225, 229))

gauche = telephone(DOSSIER / "1-accueil.png", 330)
centre = telephone(DOSSIER / "2-chat-terre.png", 380)
droite = telephone(DOSSIER / "4-chat-arabe.png", 330)
y = 360
fond.alpha_composite(gauche, (10, y + 90))
fond.alpha_composite(droite, (W - droite.width - 10, y + 90))
fond.alpha_composite(centre, ((W - centre.width) // 2, y))

bas = H - 92
d = ImageDraw.Draw(fond)
d.rounded_rectangle((70, bas - 18, W - 70, bas + 58), radius=38, fill=(200, 16, 46))
texte = "Gratuit · amena.onrender.com"
lt = d.textlength(texte, font=police(34))
d.text(((W - lt) / 2, bas - 2), texte, font=police(34), fill=(255, 255, 255))

sortie = DOSSIER / "visuel-linkedin-1200x1500.png"
fond.convert("RGB").save(sortie, optimize=True)
print(sortie)
