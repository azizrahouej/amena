"""Textes officiels intégraux (Constitution, codes, lois) extraits des PDF de data/lois_officielles.

Chaque PDF est découpé article par article (« Article 12 », « Art. 218 bis », « الفصل 3 ») et
rendu sous la même forme que les fichiers data/juridique/*.json : (pays, textes, articles). La
bibliothèque, la recherche plein texte (FTS5) et l'index du chat les prennent donc en charge
sans autre code.

La base grandit toute seule : un nouveau PDF déposé dans data/lois_officielles est découvert,
découpé et indexé à la construction suivante (et au démarrage du serveur, voir veille.py). Les
métadonnées connues (titre, référence, source, avertissement de version) sont dans
data/juridique/officiels/catalogue.json ; un PDF absent du catalogue reçoit un titre tiré de son
nom de fichier.

L'extraction est mise en cache (data/juridique/officiels/extraits.json), recalculée seulement si
un PDF change.
"""

import json
import re
import unicodedata

from .config import RACINE

DOSSIER_PDF = RACINE / "data" / "lois_officielles"
DOSSIER_META = RACINE / "data" / "juridique" / "officiels"
FICHIER_CATALOGUE = DOSSIER_META / "catalogue.json"
FICHIER_CACHE = DOSSIER_META / "extraits.json"

PAYS_TN = {"code": "TN", "nom_fr": "Tunisie", "nom_ar": "تونس", "region": "Afrique du Nord"}

_SUFFIXES = r"(?:bis|ter|quater|quinquies|sexies|septies|octies|nonies|decies)"
_MARQUEUR_FR = re.compile(
    # « Article 12 », « Art. 218 bis », « Article 5. bis », « Article 53-2 »
    rf"(?m)^[ \t]*(?:Article|ARTICLE|Art\.)[ \t]+((?i:premier)|1er|\d+(?:[ \t]*\.?[ \t-]*{_SUFFIXES}|-\d+)?)[ \t]*[.\-–:]?[ \t]*")
# Le numéro peut être sur la ligne suivante (« الفصل\n 15 »), comme dans l'édition 2004 du Code des droits réels.
_MARQUEUR_AR = re.compile(r"(?m)^[ \t]*الفصل[ \t]*\n?[ \t]*(\d+)(?:[ \t]*(مكرر|ثالثا|رابعا))?[ \t]*[:\-–.]?")

# PyMuPDF restitue mal la ligature lam-alif : « اإلساءة » au lieu de « الإساءة ».
_LIGATURES = {"اإل": "الإ", "األ": "الأ", "اآل": "الآ", "اال": "الا"}


def _corriger_arabe(texte):
    for faux, juste in _LIGATURES.items():
        texte = texte.replace(faux, juste)
    return texte


def _nettoyer(texte):
    texte = texte.replace("̶", "").replace("\xad", "")
    texte = re.sub(r"-\n(?=\w)", "", texte)          # mots coupés en fin de ligne
    texte = re.sub(r"[ \t]*\n[ \t]*", " ", texte)     # le PDF coupe les phrases en lignes
    return re.sub(r"\s{2,}", " ", texte).strip()


def _numero(brut, suffixe_ar=None):
    if brut.lower() in ("premier", "1er"):
        numero = "1"
    elif re.fullmatch(r"\d+-\d+", brut):
        numero = brut                       # « 53-2 » garde son tiret
    else:
        numero = re.sub(r"[ \t.\-]+", " ", brut).strip()   # « 5. bis » → « 5 bis »
    if suffixe_ar:
        numero += " مكرر" if suffixe_ar == "مكرر" else f" {suffixe_ar}"
    return numero


_RANG_SUFFIXE = {"bis": 1, "مكرر": 1, "ter": 2, "ثالثا": 2, "quater": 3, "رابعا": 3, "quinquies": 4,
                 "sexies": 5, "septies": 6, "octies": 7, "nonies": 8, "decies": 9}


def _cle(numero):
    """Clé d'ordre d'un numéro : « 218 » < « 218 bis » < « 218 ter » < « 219 » ; « 53-2 » après « 53 »."""
    m = re.match(r"(\d+)(?:-(\d+))?\s*(\S+)?", numero)
    if not m:
        return (0, 0)
    if m.group(2):
        return (int(m.group(1)), int(m.group(2)))
    return (int(m.group(1)), _RANG_SUFFIXE.get((m.group(3) or "").lower(), 0))


def _plus_longue_suite(articles):
    """Plus longue suite d'articles à numérotation strictement croissante.

    Écarte ce qui interrompt la numérotation du code : loi de promulgation placée avant
    (« Article premier. — Est approuvé le code… »), loi insérée au milieu, sommaire. À longueur
    égale, ce sont les articles les plus tardifs qui sont retenus : ceux du code lui-même.
    """
    from bisect import bisect_left
    cles = [_cle(a["numero"]) for a in articles]
    fins, fins_cles, precedent = [], [], [None] * len(articles)
    for i, c in enumerate(cles):
        pos = bisect_left(fins_cles, c)
        precedent[i] = fins[pos - 1] if pos > 0 else None
        if pos == len(fins):
            fins.append(i)
            fins_cles.append(c)
        else:
            fins[pos], fins_cles[pos] = i, c
    gardes, i = set(), fins[-1] if fins else None
    while i is not None:
        gardes.add(i)
        i = precedent[i]
    # Rien n'est perdu : un passage écarté au milieu du texte (par exemple « Article 218 : … »
    # cité par une loi qui modifie le Code pénal) est rattaché à l'article qui le contient.
    suite = []
    for i, a in enumerate(articles):
        if i in gardes:
            suite.append(dict(a))
        elif suite:
            suite[-1]["contenu"] = f"{suite[-1]['contenu']} « Article {a['numero']} : {a['contenu']} »"[:12000]
    return suite


def decouper_articles(texte, langue="fr"):
    """Découpe un texte brut en articles [{numero, contenu}], dans l'ordre du code."""
    marqueur = _MARQUEUR_AR if langue == "ar" else _MARQUEUR_FR
    reperes = list(marqueur.finditer(texte))
    articles = []
    for i, m in enumerate(reperes):
        fin = reperes[i + 1].start() if i + 1 < len(reperes) else len(texte)
        contenu = _nettoyer(texte[m.end():fin])
        if len(contenu) < 12:          # renvoi de sommaire, en-tête isolé
            continue
        articles.append({"numero": _numero(m.group(1), m.group(2) if langue == "ar" else None),
                         "contenu": contenu[:12000]})
    return _plus_longue_suite(articles)


def _empreinte(chemin):
    s = chemin.stat()
    return f"{s.st_size}-{int(s.st_mtime)}"


def _texte_html(chemin):
    """Texte d'une page HTML (par exemple une fiche WIPO Lex) : balises retirées, une ligne par
    bloc, scripts et styles ignorés. Bibliothèque standard uniquement."""
    from html.parser import HTMLParser

    class Lecteur(HTMLParser):
        BLOCS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}

        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.morceaux, self.ignorer = [], 0

        def handle_starttag(self, balise, attrs):
            if balise in ("script", "style", "noscript", "nav", "header", "footer"):
                self.ignorer += 1
            elif balise in self.BLOCS:
                self.morceaux.append("\n")

        def handle_endtag(self, balise):
            if balise in ("script", "style", "noscript", "nav", "header", "footer"):
                self.ignorer = max(0, self.ignorer - 1)
            elif balise in self.BLOCS:
                self.morceaux.append("\n")

        def handle_data(self, donnees):
            if not self.ignorer:
                self.morceaux.append(donnees)

    lecteur = Lecteur()
    lecteur.feed(chemin.read_text(encoding="utf-8", errors="replace"))
    return "".join(lecteur.morceaux)


def _lire_pdf(chemin):
    if chemin.suffix.lower() in (".html", ".htm"):
        texte = _texte_html(chemin)
    else:
        import fitz  # PyMuPDF
        with fitz.open(chemin) as doc:
            texte = "\n".join(page.get_text() for page in doc)
    # Certains PDF arabes stockent les « formes de présentation » (ﺍﻟﻔﺼل) : NFKC les ramène aux lettres usuelles.
    texte = unicodedata.normalize("NFKC", texte)
    arabe = len(re.findall(r"[؀-ۿ]", texte))
    langue = "ar" if arabe > len(texte) * 0.3 else "fr"
    if langue == "ar":
        texte = _corriger_arabe(texte)
    return texte, langue


def _titre_depuis_nom(nom):
    return re.sub(r"[_-]+", " ", nom).strip().capitalize()


def charger_catalogue():
    if FICHIER_CATALOGUE.exists():
        return json.loads(FICHIER_CATALOGUE.read_text(encoding="utf-8"))
    return {}


def extraire_tout(verbeux=False):
    """Renvoie {nom_fichier: {langue, articles}} en réutilisant le cache quand c'est possible."""
    if not DOSSIER_PDF.exists():
        return {}
    try:
        import fitz  # noqa: F401
    except ImportError:
        if verbeux:
            print("PyMuPDF absent : les textes officiels sont ignorés (pip install pymupdf).")
        return {}
    cache = json.loads(FICHIER_CACHE.read_text(encoding="utf-8")) if FICHIER_CACHE.exists() else {}
    resultat, change = {}, False
    documents = sorted([*DOSSIER_PDF.glob("*.pdf"), *DOSSIER_PDF.glob("*.html")])
    for pdf in documents:
        empreinte = _empreinte(pdf)
        entree = cache.get(pdf.name)
        if not entree or entree.get("empreinte") != empreinte:
            texte, langue = _lire_pdf(pdf)
            entree = {"empreinte": empreinte, "langue": langue, "caracteres": len(texte),
                      "articles": decouper_articles(texte, langue)}
            change = True
            if verbeux:
                print(f"  {pdf.name} : {len(entree['articles'])} articles extraits ({langue}).")
        resultat[pdf.name] = entree
    if change or set(cache) != set(resultat):
        DOSSIER_META.mkdir(parents=True, exist_ok=True)
        FICHIER_CACHE.write_text(json.dumps(resultat, ensure_ascii=False), encoding="utf-8")
    return resultat


def textes_officiels(verbeux=False):
    """Les textes officiels au format des fichiers juridiques : [(pays, [textes])]."""
    catalogue = charger_catalogue()
    textes = []
    for nom, entree in extraire_tout(verbeux).items():
        if not entree["articles"]:
            continue
        meta = catalogue.get(nom, {})
        identifiant = meta.get("id") or "tn-off-" + re.sub(r"[^a-z0-9]+", "-", nom.lower().removesuffix(".pdf")).strip("-")
        textes.append({
            "id": identifiant,
            "type": meta.get("type", "texte intégral"),
            "titre": meta.get("titre") or _titre_depuis_nom(nom.removesuffix(".pdf")),
            "reference": meta.get("reference", ""),
            "date": meta.get("date", ""),
            "domaines": meta.get("domaines", []) + ["texte intégral"],
            "source": meta.get("source", "Document déposé dans data/lois_officielles"),
            "url": meta.get("url"),
            "resume": meta.get("resume") or f"Texte intégral extrait du document {nom}.",
            "langue": entree["langue"],
            "articles": [{"numero": a["numero"], "titre": "", "contenu": a["contenu"]} for a in entree["articles"]],
            "analyses": [{"type": "vigilance", "contenu": meta["avertissement"]}] if meta.get("avertissement") else [],
        })
    return [(PAYS_TN, textes)] if textes else []
