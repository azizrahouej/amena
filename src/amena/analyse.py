"""Analyse juridique d'une situation, à la manière d'une note d'avocat.

Démarche :
    1. sécurité d'abord : détection d'un danger immédiat (règles + modèle de triage) ;
    2. QUALIFICATION : repérer les situations types décrites (base d'expertise
       data/juridique/qualifications.json pour les violences et la famille,
       data/juridique/situations_civiles.json pour les biens, l'argent, les terres et les contrats) ;
    3. FONDEMENTS : les articles applicables, tirés de la base juridique ;
    4. STRATÉGIE : preuves à réunir, démarches dans l'ordre, délais ;
    5. POINTS FAIBLES : risques du dossier (vigilance) et limites connues des textes invoqués,
       pour que la personne et son avocat les anticipent ;
    6. textes complémentaires trouvés par recherche plein texte.

Ce n'est pas une consultation d'avocat : la note le dit explicitement et oriente vers l'aide
juridictionnelle et les associations.
"""

import json

from . import juridique
from .config import RACINE
from .securite import anonymiser, detecter_langue, normaliser, regles_danger

BASE_EXPERTISE = json.loads((RACINE / "data" / "juridique" / "qualifications.json").read_text(encoding="utf-8"))
_CIVILES = json.loads((RACINE / "data" / "juridique" / "situations_civiles.json").read_text(encoding="utf-8"))
BASE_EXPERTISE["situations"] += [s for s in _CIVILES["situations"] if s["id"] != "generale"]
# Consultation générale : quand aucune situation n'est reconnue, la méthode d'un avocat et des
# questions pour préciser, plutôt qu'une réponse hors sujet.
SITUATION_GENERALE = next(s for s in _CIVILES["situations"] if s["id"] == "generale")
SITUATIONS_CIVILES = {s["id"] for s in _CIVILES["situations"]}
LANGUES_CONTENU = ("fr", "ar", "dz")


def localiser(s, champ, langue):
    """Le champ dans la langue de la question (« preuves_ar », « libelle_dz »…), sinon en français."""
    if langue in LANGUES_CONTENU and langue != "fr" and s.get(f"{champ}_{langue}"):
        return s[f"{champ}_{langue}"]
    return s.get(champ)


def _par_langue(valeur, langue):
    """{fr, ar, dz} → la bonne langue ; une liste ou une chaîne est renvoyée telle quelle."""
    if isinstance(valeur, dict):
        return valeur.get(langue) or valeur.get("fr")
    return valeur

AVERTISSEMENT = ("Cette analyse est une aide à la compréhension, générée automatiquement. Elle ne remplace pas "
                 "la consultation d'un avocat. L'aide juridictionnelle permet d'en obtenir un gratuitement "
                 "si vos revenus sont insuffisants ; le 1899 et les associations peuvent vous orienter.")


def _unique(elements):
    vus, sortie = set(), []
    for e in elements:
        if e not in vus:
            vus.add(e)
            sortie.append(e)
    return sortie


# Ordre de présentation : comme une avocate, on traite d'abord les faits les plus graves.
GRAVITE = ["sequestration", "travail_domestique", "violence_sexuelle", "violence_physique", "enfants",
           "violence_psychologique", "harcelement_sexuel", "cyber_violence", "auteur_infraction", "temoin_crime",
           "mis_en_cause", "logement", "vol_famille", "vol",
           "escroquerie", "abus_confiance", "propriete_fonciere", "violence_economique", "dettes_contrainte",
           "dette_impayee", "dommage_responsabilite", "travail_licenciement", "discrimination", "divorce", "acces_avocat"]


def _motif(indice):
    """Indice normalisé, en gardant ses espaces de bord : « vol » ne doit pas trouver « volontaire »."""
    coeur = normaliser(indice)
    return (" " if indice.startswith(" ") else "") + coeur + (" " if indice.endswith(" ") else "")


def detecter_situations(texte, garder_remplacees=False):
    """Renvoie les situations types reconnues, de la plus grave à la moins grave."""
    t = f" {normaliser(texte)} "
    trouvees = []
    for situation in BASE_EXPERTISE["situations"]:
        indices = [i for i in situation["indices"] if _motif(i) in t]
        # « aussi » : un second indice est exigé (vol ET parent, par exemple).
        if indices and situation.get("aussi") and not any(_motif(i) in t for i in situation["aussi"]):
            indices = []
        if indices:
            rang = GRAVITE.index(situation["id"]) if situation["id"] in GRAVITE else len(GRAVITE)
            trouvees.append((rang, situation, indices))
    trouvees.sort(key=lambda x: x[0])
    # Une situation précise rend inutiles les situations plus générales qu'elle « remplace ».
    if garder_remplacees:
        return [(s, indices) for _, s, indices in trouvees]
    remplacees = {r for _, s, _ in trouvees for r in s.get("remplace", [])}
    return [(s, indices) for _, s, indices in trouvees if s["id"] not in remplacees]


def analyser(situation, pays="TN", trieur=None, cnx=None, generale=False):
    # Le pays peut être un code de la bibliothèque (TN) ou un code ISO alpha-3 (TUN, SEN...).
    from .donnees_wbl import ISO2_VERS_ISO3
    pays = (pays or "TN").upper()
    pays = next((k for k, v in ISO2_VERS_ISO3.items() if v == pays), pays)
    texte = anonymiser((situation or "").strip()[:4000])
    langue = detecter_langue(texte)
    regle = regles_danger(texte)
    triage = trieur.predire(texte) if trieur else None
    urgence = bool(regle) or (triage is not None and triage["label"] == "urgence")

    reconnues = detecter_situations(texte) if pays == "TN" else []
    if not reconnues and generale and pays == "TN":
        reconnues = [(SITUATION_GENERALE, [])]
    lg = langue if langue in LANGUES_CONTENU else "fr"
    qualifications, cites = [], []
    preuves, demarches, delais, vigilance, questions, principes, reponses = [], [], [], [], [], [], []
    conseil = None

    toutes = detecter_situations(texte, garder_remplacees=True) if pays == "TN" else []
    for s, indices in reconnues:
        fondements = []
        # Personne mise en cause ou auteur : on garde les articles qui fixent la peine de l'infraction
        # repérée (vol, escroquerie…), sans les démarches pensées pour la victime.
        peines = [t for r, _ in toutes if r["id"] in s.get("garde_textes_de", [])
                  for t in r["textes"] if t[0] == "tn-off-code-penal" and t not in s["textes"]]
        textes = peines + list(s["textes"])  # « ce que vous risquez » d'abord, puis vos droits
        explications_tout = {**{k: v for r, _ in toutes if r["id"] in s.get("garde_textes_de", [])
                                for k, v in (r.get("explications") or {}).items()}, **(s.get("explications") or {})}
        for texte_id, numero in textes:
            a = juridique.article(texte_id, numero, cnx)
            if a:
                explication = explications_tout.get(f"{texte_id}#{numero}")
                fondements.append({"texte_id": texte_id, "texte": a["texte_titre"], "reference": a["reference"],
                                   "article": a["numero"], "titre": a["titre"], "contenu": a["contenu"],
                                   "explication": _par_langue(explication, lg) if explication else None})
                cites.append(texte_id)
        qualifications.append({"id": s["id"], "libelle": localiser(s, "libelle", lg),
                               "qualification": localiser(s, "qualification", lg),
                               "indices": indices, "fondements": fondements})
        preuves += localiser(s, "preuves", lg)
        demarches += localiser(s, "demarches", lg)
        delais += localiser(s, "delais", lg)
        vigilance += localiser(s, "vigilance", lg)
        principes += [_par_langue(p, lg) for p in s.get("principes", [])]
        questions += _par_langue(s.get("questions", {}), lg) or []
        reponses += _par_langue(s.get("reponses", {}), lg) or []
        conseil = conseil or _par_langue(s.get("conseil"), lg)

    if urgence:
        demarches.insert(0, {"fr": "Danger immédiat : appelez le 197 (police) ou le 193 (garde nationale) avant toute autre démarche",
                             "ar": "خطر فوري: اتصل بالرقم 197 (الشرطة) أو 193 (الحرس الوطني) قبل أي إجراء آخر",
                             "dz": "Khatar tawa : kallem el 197 (police) walla el 193 (7aras) 9bal kol chay"}[lg])

    # Recherche plein texte : textes pertinents non encore cités (utile aussi hors Tunisie).
    complementaires = [r for r in juridique.rechercher(texte, pays=pays, limite=8, cnx=cnx)
                       if r["texte_id"] not in cites][:5]

    limites = [a for a in juridique.analyses_de(_unique(cites), cnx) if a["type"] in ("lacune", "vigilance")]

    # Regard international : acquis et lacunes relevés par la Banque mondiale (WBL 2026),
    # disponible pour 190 pays, y compris ceux absents de la bibliothèque.
    international = juridique.regard_international(pays, cnx)

    return {
        "langue": langue,
        "pays": pays,
        "urgence": urgence,
        "raison_urgence": regle or (triage["raison"] if urgence and triage else None),
        "qualifications": qualifications,
        "preuves": _unique(preuves),
        "demarches": _unique(demarches),
        "delais": _unique(delais),
        "vigilance": _unique(vigilance),
        "limites_loi": limites,
        "principes": _unique(principes),
        "questions": _unique(questions)[:4],
        "reponses": _unique(reponses)[:4],
        "conseil": conseil,
        "generale": bool(reconnues) and reconnues[0][0]["id"] == "generale",
        "textes_complementaires": complementaires,
        "regard_international": international,
        "couverture": ("complete" if qualifications else "textes_seuls"),
        "avertissement": AVERTISSEMENT,
    }
