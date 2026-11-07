"""Construction de la base de connaissances : documents -> chunks.jsonl.

Même démarche que la séance « Du PDF aux chunks » :
    - on garde la structure du document (chemin de titres) ;
    - on découpe par sections, puis par phrases avec recouvrement ;
    - on préfixe chaque chunk par son chemin de titres pour qu'il se comprenne seul.

Sources acceptées :
    data/knowledge_base/*.md   fiches rédigées par l'équipe (titres markdown #, ##)
    data/pdf/*.pdf             documents officiels (ex. texte de loi), si PyMuPDF est installé
"""

import json
import re

from .config import (CHUNK_CIBLE, CHUNK_MINIMUM, CHUNK_OVERLAP, DOSSIER_KB,
                     DOSSIER_PDF, FICHIER_CHUNKS)


def compter_tokens(texte):
    """Estimation : environ 3,8 caractères par token en français."""
    return max(1, round(len(texte) / 3.8))


def en_phrases(texte):
    """Coupe un texte en phrases (ponctuation latine et arabe)."""
    phrases = re.split(r"(?<=[.!?؟])\s+", texte)
    return [p.strip() for p in phrases if p.strip()]


def decouper(texte):
    """Découpe une section en morceaux d'environ CHUNK_CIBLE tokens, avec recouvrement."""
    if compter_tokens(texte) <= CHUNK_CIBLE:
        return [texte] if compter_tokens(texte) >= CHUNK_MINIMUM else []

    morceaux, courant, total = [], [], 0
    for phrase in en_phrases(texte):
        taille = compter_tokens(phrase)
        if total + taille > CHUNK_CIBLE and courant:
            morceaux.append(" ".join(courant))
            # Recouvrement : on reprend les dernières phrases du chunk fermé.
            reprise, compte = [], 0
            for p in reversed(courant):
                compte += compter_tokens(p)
                reprise.insert(0, p)
                if compte >= CHUNK_OVERLAP:
                    break
            courant, total = reprise, compte
        courant.append(phrase)
        total += taille
    if courant:
        morceaux.append(" ".join(courant))
    return morceaux


def sections_markdown(chemin_fichier):
    """Lit un fichier markdown et renvoie ses sections avec leur chemin de titres."""
    sections, titres, tampon = [], {}, []

    def fermer():
        texte = " ".join(tampon).strip()
        if texte:
            chemin = [titres[n] for n in sorted(titres)]
            sections.append({"chemin": chemin, "texte": texte})
        tampon.clear()

    for ligne in chemin_fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        titre = re.match(r"^(#{1,6})\s+(.*)", ligne)
        if titre:
            fermer()
            niveau = len(titre.group(1))
            titres[niveau] = titre.group(2).strip()
            # Un nouveau titre annule les sous-titres qui en dépendaient.
            for plus_profond in [n for n in titres if n > niveau]:
                del titres[plus_profond]
        elif ligne.startswith(">"):
            continue  # avertissements éditoriaux : utiles au lecteur, pas à la recherche
        elif ligne:
            tampon.append(ligne)
    fermer()
    return sections


def sections_pdf(chemin_fichier):
    """Version simplifiée de l'extraction PyMuPDF de la séance 1 : une section par page."""
    import fitz  # PyMuPDF, dépendance optionnelle

    sections = []
    with fitz.open(chemin_fichier) as document:
        for num_page, page in enumerate(document, start=1):
            texte = re.sub(r"\s+", " ", page.get_text()).strip()
            texte = re.sub(r"(\w)-\s+(\w)", r"\1\2", texte)
            if len(texte) > 80:
                sections.append({"chemin": [chemin_fichier.stem, f"page {num_page}"],
                                 "texte": texte})
    return sections


def construire_chunks():
    """Parcourt toutes les sources et écrit chunks.jsonl. Renvoie la liste des chunks."""
    sources = [(f, sections_markdown) for f in sorted(DOSSIER_KB.glob("*.md"))]
    if DOSSIER_PDF.exists():
        try:
            import fitz  # noqa: F401
            sources += [(f, sections_pdf) for f in sorted(DOSSIER_PDF.glob("*.pdf"))]
        except ImportError:
            print("PyMuPDF absent : les PDF de data/pdf sont ignorés (pip install pymupdf).")

    chunks = []
    for fichier, lecteur in sources:
        for section in lecteur(fichier):
            for position, morceau in enumerate(decouper(section["texte"]), start=1):
                fil = " > ".join(section["chemin"])
                chunks.append({
                    "id": f"chunk_{len(chunks):04d}",
                    "texte": f"{fil}\n\n{morceau}",
                    "metadata": {
                        "source": fichier.name,
                        "type": "fiche",
                        "element": f"fiche:{fichier.stem}",
                        "chemin": section["chemin"],
                        "position": position,
                        "n_tokens": compter_tokens(morceau),
                    },
                })

    # Bibliothèque juridique : chaque article est un passage, préfixé par son pays et son texte.
    from .juridique import tous_les_articles
    for pays, texte, art in tous_les_articles():
        chemin = [pays["nom_fr"], texte["titre"], f"Art. {art.get('numero')} — {art.get('titre', '')}".strip(" —")]
        chunks.append({
            "id": f"chunk_{len(chunks):04d}",
            "texte": f"{' > '.join(chemin)}\n\n{art['contenu']} (Réf. : {texte.get('reference', '')})",
            "metadata": {
                "source": f"loi:{texte['id']}",
                "type": "loi",
                "element": f"loi:{texte['id']}",
                "pays": pays["code"],
                "chemin": chemin,
                "position": 1,
                "n_tokens": compter_tokens(art["contenu"]),
            },
        })

    FICHIER_CHUNKS.parent.mkdir(parents=True, exist_ok=True)
    with open(FICHIER_CHUNKS, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    return chunks


def charger_chunks():
    with open(FICHIER_CHUNKS, encoding="utf-8") as f:
        return [json.loads(ligne) for ligne in f]
