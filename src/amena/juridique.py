"""Bibliothèque juridique : chargement des textes de loi et requêtes.

Les textes sont décrits dans data/juridique/*.json (un fichier par pays ou par zone), puis
chargés dans SQLite. Ajouter un pays = ajouter un fichier JSON et relancer la construction.
Les contenus d'articles sont des RÉSUMÉS rédigés pour le projet : chaque texte indique sa
référence officielle, à consulter avant toute démarche.
"""

import json
import re

from .base import connexion, lignes
from .config import RACINE

DOSSIER_JURIDIQUE = RACINE / "data" / "juridique"


def _fichiers_sources():
    """Renvoie [(pays, textes)] à partir de tous les fichiers JSON du dossier."""
    blocs = []
    for fichier in sorted(DOSSIER_JURIDIQUE.glob("*.json")):
        if fichier.name in ("qualifications.json", "situations_civiles.json"):  # bases d'expertise, pas des lois
            continue
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        if "pays_multiples" in donnees:
            blocs += [(b["pays"], b["textes"]) for b in donnees["pays_multiples"]]
        else:
            blocs.append((donnees["pays"], donnees["textes"]))
    # Textes officiels intégraux extraits des PDF (Constitution, codes, lois) : même format.
    from .officiels import textes_officiels
    return blocs + textes_officiels()


def charger_bibliotheque(cnx=None):
    """(Re)construit les tables juridiques. Les comptes et interactions ne sont pas touchés."""
    cnx = cnx or connexion()
    with cnx:
        # Une table FTS5 sans contenu se vide avec la commande spéciale 'delete-all'.
        cnx.execute("INSERT INTO articles_fts (articles_fts) VALUES ('delete-all')")
        for table in ("analyses", "articles", "textes", "pays"):
            cnx.execute(f"DELETE FROM {table}")
        for pays, textes in _fichiers_sources():
            # Un même pays peut être réparti sur plusieurs fichiers (tn.json, tn_complements.json).
            cnx.execute("INSERT OR IGNORE INTO pays VALUES (:code, :nom_fr, :nom_ar, :region)", pays)
            for t in textes:
                cnx.execute(
                    "INSERT INTO textes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (t["id"], pays["code"], t.get("type"), t["titre"], t.get("reference"), t.get("date"),
                     ",".join(t.get("domaines", [])), t.get("source"), t.get("url"), t.get("resume")))
                for position, a in enumerate(t.get("articles", [])):
                    curseur = cnx.execute(
                        "INSERT INTO articles (texte_id, numero, titre, contenu, position) VALUES (?, ?, ?, ?, ?)",
                        (t["id"], a.get("numero"), a.get("titre"), a["contenu"], position))
                    cnx.execute("INSERT INTO articles_fts (rowid, titre_texte, numero, titre, contenu) VALUES (?, ?, ?, ?, ?)",
                                (curseur.lastrowid, t["titre"], a.get("numero"), a.get("titre"), a["contenu"]))
                for analyse in t.get("analyses", []):
                    cnx.execute("INSERT INTO analyses (texte_id, type, contenu) VALUES (?, ?, ?)",
                                (t["id"], analyse["type"], analyse["contenu"]))
    return statistiques(cnx)


def statistiques(cnx=None):
    cnx = cnx or connexion()
    compter = lambda table: cnx.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: E731
    return {"pays": compter("pays"), "textes": compter("textes"),
            "articles": compter("articles"), "analyses": compter("analyses"),
            "pays_monde": compter("monde_pays"), "indicateurs_monde": compter("monde_indicateurs")}


def lister_pays(cnx=None):
    cnx = cnx or connexion()
    return lignes(cnx.execute("""
        SELECT p.*, COUNT(t.id) AS nb_textes FROM pays p LEFT JOIN textes t ON t.pays = p.code
        GROUP BY p.code ORDER BY p.code = 'TN' DESC, p.code = 'INT' DESC, p.nom_fr"""))


def lister_textes(pays=None, domaine=None, type_=None, cnx=None):
    cnx = cnx or connexion()
    conditions, params = [], []
    if pays:
        conditions.append("t.pays = ?"); params.append(pays)
    if domaine:
        conditions.append("(',' || t.domaines || ',') LIKE ?"); params.append(f"%,{domaine},%")
    if type_:
        conditions.append("t.type = ?"); params.append(type_)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    textes = lignes(cnx.execute(f"""
        SELECT t.*, p.nom_fr AS pays_nom, p.nom_ar AS pays_nom_ar,
               (SELECT COUNT(*) FROM articles a WHERE a.texte_id = t.id) AS nb_articles,
               (SELECT COUNT(*) FROM analyses n WHERE n.texte_id = t.id AND n.type = 'lacune') AS nb_lacunes
        FROM textes t JOIN pays p ON p.code = t.pays {where}
        ORDER BY t.pays = 'TN' DESC, t.date DESC""", params))
    for t in textes:
        t["domaines"] = [d for d in (t["domaines"] or "").split(",") if d]
    return textes


def detail_texte(texte_id, cnx=None):
    cnx = cnx or connexion()
    texte = cnx.execute("""SELECT t.*, p.nom_fr AS pays_nom, p.nom_ar AS pays_nom_ar
                           FROM textes t JOIN pays p ON p.code = t.pays WHERE t.id = ?""", (texte_id,)).fetchone()
    if texte is None:
        return None
    texte = dict(texte)
    texte["domaines"] = [d for d in (texte["domaines"] or "").split(",") if d]
    texte["articles"] = lignes(cnx.execute(
        "SELECT numero, titre, contenu FROM articles WHERE texte_id = ? ORDER BY position", (texte_id,)))
    texte["analyses"] = lignes(cnx.execute(
        "SELECT type, contenu FROM analyses WHERE texte_id = ? ORDER BY type, id", (texte_id,)))
    return texte


def article(texte_id, numero, cnx=None):
    cnx = cnx or connexion()
    ligne = cnx.execute("""SELECT a.numero, a.titre, a.contenu, t.id AS texte_id, t.titre AS texte_titre,
                                  t.reference, t.pays FROM articles a JOIN textes t ON t.id = a.texte_id
                           WHERE a.texte_id = ? AND a.numero = ?""", (texte_id, numero)).fetchone()
    return dict(ligne) if ligne else None


def analyses_de(texte_ids, cnx=None):
    cnx = cnx or connexion()
    if not texte_ids:
        return []
    marques = ",".join("?" * len(texte_ids))
    return lignes(cnx.execute(f"""SELECT n.type, n.contenu, t.id AS texte_id, t.titre AS texte_titre
                                  FROM analyses n JOIN textes t ON t.id = n.texte_id
                                  WHERE n.texte_id IN ({marques})""", list(texte_ids)))


def rechercher(question, pays=None, limite=8, cnx=None):
    """Recherche plein texte (FTS5, classement BM25) dans les articles."""
    cnx = cnx or connexion()
    mots = [m for m in re.findall(r"\w{3,}", question.lower())]
    if not mots:
        return []
    # OR entre les mots : BM25 fait remonter les articles qui en contiennent le plus.
    requete = " OR ".join(f'"{m}"' for m in mots[:20])
    filtre, params = "", [requete]
    if pays:
        filtre = "AND t.pays IN (?, 'INT')"
        params.append(pays)
    params.append(limite)
    return lignes(cnx.execute(f"""
        SELECT a.numero, a.titre, a.contenu, t.id AS texte_id, t.titre AS texte_titre, t.pays,
               bm25(articles_fts) AS score
        FROM articles_fts JOIN articles a ON a.id = articles_fts.rowid JOIN textes t ON t.id = a.texte_id
        WHERE articles_fts MATCH ? {filtre}
        ORDER BY score LIMIT ?""", params))


# --- Données mondiales (Banque mondiale, WBL 2026) ---------------------------

def _iso3(code, cnx):
    """Accepte un code de la bibliothèque (TN) ou un code ISO alpha-3 (TUN)."""
    from .donnees_wbl import ISO2_VERS_ISO3
    code = (code or "").upper()
    code = ISO2_VERS_ISO3.get(code, code)
    return code if cnx.execute("SELECT 1 FROM monde_pays WHERE iso3 = ?", (code,)).fetchone() else None


def lister_monde(cnx=None):
    """Tous les pays avec leurs scores et les réponses clés, pour l'atlas."""
    cnx = cnx or connexion()
    pays = lignes(cnx.execute("SELECT * FROM monde_pays ORDER BY pays_fr"))
    cles = ("Saf_Law_DomViolLaw", "Saf_Law_DomViol_ProtOrd", "Saf_Law_DomViol_SexualMR", "Saf_Law_SexHar_EplCpCr",
            "Saf_Law_SexHar_PubCpCr", "Saf_Law_SexHar_CybCpCr", "Saf_Law_FemicideCr", "Saf_Law_ChildMarr_Age",
            "Saf_SFR_Services_Shelter")
    reponses = {}
    for r in cnx.execute(f"SELECT iso3, code, reponse FROM monde_indicateurs WHERE code IN ({','.join('?' * len(cles))})", cles):
        reponses.setdefault(r["iso3"], {})[r["code"]] = None if r["reponse"] is None else bool(r["reponse"])
    for p in pays:
        p["reponses"] = reponses.get(p["iso3"], {})
    return pays


def detail_monde(code, cnx=None):
    cnx = cnx or connexion()
    iso3 = _iso3(code, cnx)
    if iso3 is None:
        return None
    pays = dict(cnx.execute("SELECT * FROM monde_pays WHERE iso3 = ?", (iso3,)).fetchone())
    moyennes = cnx.execute("""SELECT AVG(score_cadre_legal) AS cadre, AVG(score_dispositifs) AS dispositifs,
                                     AVG(score_application) AS application, COUNT(*) AS n
                              FROM monde_pays WHERE region_fr = ?""", (pays["region_fr"],)).fetchone()
    mondiales = cnx.execute("""SELECT AVG(score_cadre_legal) AS cadre, AVG(score_dispositifs) AS dispositifs,
                                      AVG(score_application) AS application FROM monde_pays""").fetchone()
    pays["moyenne_region"] = {k: round(moyennes[k], 1) if moyennes[k] is not None else None for k in ("cadre", "dispositifs", "application")}
    pays["moyenne_region"]["n"] = moyennes["n"]
    pays["moyenne_monde"] = {k: round(mondiales[k], 1) for k in ("cadre", "dispositifs", "application")}
    pays["rang_cadre"] = cnx.execute("SELECT COUNT(*) + 1 FROM monde_pays WHERE score_cadre_legal > ?",
                                     (pays["score_cadre_legal"],)).fetchone()[0]
    pays["indicateurs"] = lignes(cnx.execute(
        "SELECT code, pilier, theme, question, reponse, base_legale FROM monde_indicateurs WHERE iso3 = ? ORDER BY rowid",
        (iso3,)))
    for i in pays["indicateurs"]:
        i["reponse"] = None if i["reponse"] is None else bool(i["reponse"])
    # Lien vers la bibliothèque juridique si le pays y figure.
    from .donnees_wbl import ISO2_VERS_ISO3
    iso2 = next((k for k, v in ISO2_VERS_ISO3.items() if v == iso3), None)
    pays["code_bibliotheque"] = iso2
    from .donnees_wbl import CITATION
    pays["source"] = CITATION
    return pays


def regard_international(code, cnx=None):
    """Ce que la Banque mondiale relève pour un pays : acquis (avec base légale) et lacunes."""
    detail = detail_monde(code, cnx)
    if detail is None:
        return None
    cadre = [i for i in detail["indicateurs"] if i["pilier"] == "cadre_legal"]
    return {
        "iso3": detail["iso3"], "pays": detail["pays_fr"], "source": detail["source"],
        "score_cadre_legal": detail["score_cadre_legal"], "moyenne_region": detail["moyenne_region"]["cadre"],
        "acquis": [{"theme": i["theme"], "question": i["question"], "base_legale": i["base_legale"]}
                   for i in cadre if i["reponse"] is True and i["base_legale"]],
        "lacunes": [{"theme": i["theme"], "question": i["question"]}
                    for i in detail["indicateurs"] if i["reponse"] is False],
    }


def resume_monde(code, cnx=None):
    """Résumé en une phrase par thème, utilisé comme passage par le chatbot."""
    d = detail_monde(code, cnx)
    if d is None:
        return None
    lignes_resume = [f"{d['pays_fr']}, selon la Banque mondiale (WBL 2026) : score du cadre légal de sécurité "
                     f"{d['score_cadre_legal']:.0f}/100, moyenne régionale {d['moyenne_region']['cadre']:.0f}/100."]
    for theme in dict.fromkeys(i["theme"] for i in d["indicateurs"] if i["pilier"] == "cadre_legal"):
        elements = [i for i in d["indicateurs"] if i["theme"] == theme and i["reponse"] is not None]
        oui = [i for i in elements if i["reponse"]]
        non = [i for i in elements if not i["reponse"]]
        ligne = f"{theme} : {len(oui)} garantie(s) sur {len(elements)}"
        base = next((i["base_legale"] for i in oui if i["base_legale"]), None)
        if base:
            ligne += f", base légale : {base[:110]}"
        if non:
            ligne += f". Lacune relevée (réponse « non ») : « {non[0]['question']} »"
        lignes_resume.append(ligne + ".")
    # Une ligne par thème : le mode extractif les présente telles quelles, en liste.
    return "\n".join(lignes_resume)


def detecter_pays(texte, cnx=None):
    """Repère un pays cité dans un message (noms français ou anglais)."""
    from .securite import normaliser
    cnx = cnx or connexion()
    t = f" {normaliser(texte)} "
    candidats = []
    for r in cnx.execute("SELECT iso3, pays_fr, pays_en FROM monde_pays"):
        for nom in {r["pays_fr"], r["pays_en"]}:
            n = normaliser(nom.split(",")[0])
            if len(n) >= 4 and re.search(rf"(?<!\w){re.escape(n)}(?!\w)", t):
                candidats.append((len(n), r["iso3"]))
    return max(candidats)[1] if candidats else None


def tous_les_articles():
    """Pour l'index du chatbot : chaque article devient un passage recherchable."""
    for pays, textes in _fichiers_sources():
        for t in textes:
            for a in t.get("articles", []):
                yield pays, t, a
