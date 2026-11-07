"""Recherche externe encadrée : quand la base ne connaît pas une loi ou un problème.

Principes (protection de la vie privée et fiabilité) :
    - désactivée par défaut ; activée par AMENA_RECHERCHE_EXTERNE=1 et une clé d'API de moteur de
      recherche dans l'environnement (BRAVE_API_KEY) : jamais de clé écrite dans le code ;
    - la requête envoyée ne contient JAMAIS le message de la personne : seulement des mots-clés
      juridiques tirés du message déjà anonymisé, plus « Tunisie » ;
    - la recherche est limitée à des sites juridiques officiels ou reconnus (SITES_FIABLES) ;
    - chaque résultat est enregistré dans la table sources_externes avec le statut « a_verifier » :
      il apparaît comme piste, avec son lien, mais n'entre pas dans la base vérifiée tant qu'une
      personne ne l'a pas validé (statut « valide »).
"""

import os
import re
import time
from datetime import datetime, timezone

from .base import connexion
from .securite import normaliser

SITES_FIABLES = ["legislation.tn", "iort.gov.tn", "idaraty.tn", "juridoc.tn", "faolex.fao.org", "wipo.int",
                 "cawtar.org", "justice.gov.tn", "arp.tn", "inpdp.tn"]
URL_BRAVE = "https://api.search.brave.com/res/v1/web/search"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources_externes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requete TEXT NOT NULL,          -- mots-clés juridiques seulement, jamais le message
    url TEXT NOT NULL UNIQUE,
    titre TEXT,
    extrait TEXT,
    site TEXT,
    statut TEXT NOT NULL DEFAULT 'a_verifier',   -- a_verifier | valide | rejete
    trouve_le TEXT NOT NULL,
    vu INTEGER NOT NULL DEFAULT 1
);
"""

# Mots outils et mots du récit qui n'aident pas à trouver une loi (fr, derja, ar).
_VIDES = set("""
je j me m moi mon ma mes tu te toi ton ta tes il elle on nous vous ils elles le la les l un une des de du d au aux
et ou mais donc or ni car que qu qui quoi dont ce cet cette ces est sont ai a as ont avait suis etait fait faire
pour par sur dans avec sans sous chez depuis pendant plus moins tres bien pas ne n y en se s sa son ses leur leurs
comment quand pourquoi quel quelle quels quelles est-ce ca cela ceci tout tous toute toutes rien quelqu quelque
bonjour merci svp aide aider besoin veux voudrais peux puis dois savoir faire quoi droit droits loi lois
ena enti inti howa hiya 3andi andi famma chnowa kifech 3lech wa9tech w walla ken mouch ma bech elli fi el men
انا انت هو هي في من على الى عن ما ماذا كيف هل لي عندي مع هذا هذه التي الذي و او
""".split())


def active():
    return os.getenv("AMENA_RECHERCHE_EXTERNE", "0") == "1" and bool(os.getenv("BRAVE_API_KEY"))


_VOCABULAIRE = []


def vocabulaire_juridique():
    """Les mots des textes officiels de la base : seuls ceux-là partent vers le moteur de recherche,
    ce qui écarte d'office prénoms, noms de lieux et détails personnels."""
    if not _VOCABULAIRE:
        import json
        from .officiels import FICHIER_CACHE
        mots = set()
        if FICHIER_CACHE.exists():
            for entree in json.loads(FICHIER_CACHE.read_text(encoding="utf-8")).values():
                for a in entree["articles"]:
                    mots.update(re.findall(r"[\w؀-ۿ]{3,}", normaliser(a["contenu"])))
        _VOCABULAIRE.append(mots)
    return _VOCABULAIRE[0]


def mots_cles(texte, maximum=6):
    """Mots-clés juridiques du message anonymisé (les [NUMERO], [EMAIL]… sont écartés)."""
    vocab = vocabulaire_juridique()
    texte = re.sub(r"\[[A-Z_]+\]", " ", texte or "")
    mots = re.findall(r"[\w؀-ۿ'-]{3,}", normaliser(texte))
    vus, sortie = set(), []
    for m in mots:
        m = m.strip("'-")
        if m in _VIDES or m.isdigit() or m in vus or len(m) < 3 or (vocab and m not in vocab):
            continue
        vus.add(m)
        sortie.append(m)
    return sortie[:maximum]


def construire_requete(texte):
    mots = mots_cles(texte)
    if not mots:
        return None
    sites = " OR ".join(f"site:{s}" for s in SITES_FIABLES)
    return f"{' '.join(mots)} Tunisie loi ({sites})"


def _site(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().removeprefix("www.") if m else ""


def _fiable(url):
    site = _site(url)
    return any(site == s or site.endswith("." + s) for s in SITES_FIABLES)


def _interroger_brave(requete, nombre=5):
    import httpx
    r = httpx.get(URL_BRAVE, params={"q": requete, "count": nombre, "search_lang": "fr", "safesearch": "strict"},
                  headers={"Accept": "application/json", "X-Subscription-Token": os.environ["BRAVE_API_KEY"]},
                  timeout=6)
    r.raise_for_status()
    return [{"url": x.get("url"), "titre": x.get("title"), "extrait": re.sub("<[^>]+>", "", x.get("description") or "")}
            for x in r.json().get("web", {}).get("results", [])]


def enregistrer(requete, resultats, cnx=None):
    cnx = cnx or connexion()
    cnx.executescript(SCHEMA)
    maintenant = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for r in resultats:
        cnx.execute("""INSERT INTO sources_externes (requete, url, titre, extrait, site, trouve_le)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(url) DO UPDATE SET vu = vu + 1""",
                    (requete, r["url"], (r.get("titre") or "")[:300], (r.get("extrait") or "")[:600], _site(r["url"]), maintenant))
    cnx.commit()


def connues(requete_mots, cnx=None, limite=3):
    """Pistes déjà enregistrées pour des mots-clés proches (évite de réinterroger le moteur)."""
    cnx = cnx or connexion()
    cnx.executescript(SCHEMA)
    lignes = cnx.execute("SELECT url, titre, extrait, site, statut, requete FROM sources_externes "
                         "WHERE statut != 'rejete' ORDER BY statut = 'valide' DESC, vu DESC LIMIT 200").fetchall()
    cible = set(requete_mots)
    notees = [(len(cible & set((l["requete"] or "").split())), dict(l)) for l in lignes]
    return [l for score, l in sorted(notees, key=lambda x: -x[0]) if score >= 2][:limite]


_DERNIER_APPEL = [0.0]


def rechercher(texte, cnx=None, interroger=None):
    """Pistes en ligne pour un message que la base ne couvre pas. Ne lève jamais d'exception."""
    try:
        mots = mots_cles(texte)
        requete = construire_requete(texte)
        if not requete:
            return []
        deja = connues(mots, cnx)
        if deja:
            return deja
        if interroger is None:
            if not active():
                return []
            if time.time() - _DERNIER_APPEL[0] < 1.0:   # pas plus d'un appel par seconde
                return []
            _DERNIER_APPEL[0] = time.time()
            interroger = _interroger_brave
        resultats = [r for r in interroger(requete) if r.get("url") and _fiable(r["url"])][:3]
        if resultats:
            enregistrer(" ".join(mots), resultats, cnx)
        return [{**r, "site": _site(r["url"]), "statut": "a_verifier"} for r in resultats]
    except Exception as erreur:  # réseau, quota, clé invalide : la réponse se fait sans
        print(f"[AMENA] recherche externe indisponible ({type(erreur).__name__}).")
        return []


TITRE = {"fr": "Pistes trouvées en ligne (à vérifier)", "ar": "مصادر وُجدت على الإنترنت (للتثبت)",
         "dz": "Ma3loumet l9inaha 3al internet (lazem tthabbet)"}
AVERTISSEMENT = {
    "fr": "Ces textes viennent de sites juridiques officiels ou reconnus, mais je ne les ai pas encore vérifiés : ouvrez le lien et confirmez avec un avocat.",
    "ar": "هذه النصوص من مواقع قانونية رسمية أو معروفة، لكن لم يتم التثبت منها بعد: افتح الرابط وتأكد مع محام.",
    "dz": "El nousous hédhi men sites 9anouniya rasmiya, ama mezelt ma thabbattech fihom : 7ell el lien w thabbet m3a avocat.",
}


def bloc_reponse(pistes, langue="fr"):
    if not pistes:
        return ""
    lg = langue if langue in TITRE else "fr"
    lignes = [f"- [{p.get('titre') or p['site']}]({p['url']}) — {(p.get('extrait') or '')[:220]}" for p in pistes]
    return f"\n\n### {TITRE[lg]}\n" + "\n".join(lignes) + f"\n\n_{AVERTISSEMENT[lg]}_"
