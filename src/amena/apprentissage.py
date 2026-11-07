"""Auto-apprentissage à partir des avis (👍 / 👎), sans conserver aucun message.

Principe (apprentissage par renforcement simple, de type « bandit ») :
    - chaque réponse porte une CLÉ DE SITUATION, par exemple « juridique:violence_physique »
      (catégorie du triage + première situation reconnue par la base d'expertise) ;
    - quand l'utilisatrice juge la réponse utile ou non, chaque SOURCE citée reçoit un point
      « utile » ou « pas utile » pour cette clé ;
    - à la recherche suivante dans la même situation, le score de chaque source est multiplié
      par un facteur tiré de ces avis (lissage de Laplace) : les sources jugées utiles
      remontent, les autres descendent.

Seuls des identifiants de sources et des compteurs sont stockés : ni texte, ni identifiant de
personne. Désactivation : AMENA_APPRENTISSAGE=0.
"""

import os

from .base import connexion, lignes

ACTIF = os.getenv("AMENA_APPRENTISSAGE", "1") == "1"
FORCE = 0.6  # amplitude maximale du reclassement (+/- 60 %)

SCHEMA = """
CREATE TABLE IF NOT EXISTS apprentissage (
    cle TEXT NOT NULL, element TEXT NOT NULL,
    utile INTEGER NOT NULL DEFAULT 0, pas_utile INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (cle, element)
);
"""


def _cnx(cnx=None):
    cnx = cnx or connexion()
    cnx.executescript(SCHEMA)
    return cnx


def cle_apprentissage(triage, expertise=None):
    situation = expertise["qualifications"][0]["id"] if expertise and expertise.get("qualifications") else "general"
    return f"{triage['label']}:{situation}"


def identifiant(source):
    """Identifiant stable d'une source : la fiche ou le texte, et la section."""
    meta = source["metadata"]
    return f"{meta.get('element') or meta.get('source')}#{meta.get('chemin', [''])[-1]}"


def enregistrer_avis(cle, elements, utile, cnx=None, poids=1.0):
    """Ajoute un avis. poids = 1 pour un 👍 / 👎 explicite ; moins pour un signal implicite
    (source ouverte, réponse copiée, réponse régénérée), que l'IA apprend sans rien demander."""
    if not ACTIF or not cle or not elements:
        return 0
    poids = max(0.05, min(1.0, float(poids)))
    cnx = _cnx(cnx)
    colonne = "utile" if utile else "pas_utile"
    with cnx:
        for element in elements[:8]:
            cnx.execute(f"""INSERT INTO apprentissage (cle, element, {colonne}) VALUES (?, ?, ?)
                            ON CONFLICT (cle, element) DO UPDATE SET {colonne} = {colonne} + excluded.{colonne}""",
                        (cle[:80], str(element)[:200], poids))
    return len(elements[:8])


def facteur(utile, pas_utile):
    """Entre 1 - FORCE et 1 + FORCE ; vaut 1 sans avis (lissage de Laplace)."""
    return 1 + FORCE * (utile - pas_utile) / (utile + pas_utile + 2)


def reclasser(sources, cle, cnx=None):
    """Réordonne les sources selon les avis déjà donnés dans cette situation."""
    if not ACTIF or not sources:
        return sources
    cnx = _cnx(cnx)
    avis = {r["element"]: (r["utile"], r["pas_utile"])
            for r in cnx.execute("SELECT element, utile, pas_utile FROM apprentissage WHERE cle = ?", (cle,))}
    if not avis:
        return sources
    notes = []
    for rang, s in enumerate(sources):
        u, p = avis.get(identifiant(s), (0, 0))
        notes.append((s.get("score", 0) * facteur(u, p), -rang, s))
    notes.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [{**s, "score": round(score, 4)} for score, _, s in notes]


def bilan(cnx=None):
    cnx = _cnx(cnx)
    total = cnx.execute("SELECT COUNT(*), COALESCE(SUM(utile), 0), COALESCE(SUM(pas_utile), 0) FROM apprentissage").fetchone()
    meilleures = lignes(cnx.execute("""SELECT cle, element, utile, pas_utile FROM apprentissage
                                       ORDER BY utile - pas_utile DESC LIMIT 5"""))
    return {"actif": ACTIF, "associations": total[0], "avis_utiles": total[1], "avis_negatifs": total[2],
            "meilleures": meilleures}
