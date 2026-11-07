"""API web d'AMENA (FastAPI) et service de l'interface.

Lancement :  uvicorn amena.api:app --app-dir src --port 8000
Documentation interactive : http://localhost:8000/docs
"""

import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, analyse, comptes, juridique, limites, risque
from .assistant import Assistant
from .comptes import ErreurCompte
from .config import DOSSIER_KB, DOSSIER_WEB, RACINE, RAPPORT_EVALUATION
from . import veille
from .apprentissage import bilan as bilan_apprentissage, enregistrer_avis
from .generation import prechauffer, synthese_juridique
from .ingestion import sections_markdown
from .recommandation import Recommandeur
from .securite import anonymiser
from .statistiques import Statistiques

COOKIE = "amena_session"
_assistant = None
_recommandeur = None
stats = Statistiques()


def assistant():
    global _assistant
    if _assistant is None:
        _assistant = Assistant.charger()
    return _assistant


def recommandeur():
    global _recommandeur
    if _recommandeur is None:
        _recommandeur = Recommandeur()
    return _recommandeur


@asynccontextmanager
async def cycle_de_vie(_app):
    assistant()  # charge les modèles et construit la base si besoin, une seule fois
    prechauffer()  # charge le modèle local (Ollama) en mémoire, en arrière-plan
    # Veille : un texte officiel déposé ou une fiche modifiée est intégré tout seul.
    veille.demarrer(apres=recharger_assistant)
    yield


def recharger_assistant():
    """Appelée par la veille après une reconstruction : le prochain message utilise le nouvel index."""
    global _assistant
    _assistant = Assistant.charger()


app = FastAPI(
    title="AMENA API",
    description="Assistant avocat IA : droit tunisien expliqué à tous (travail, contrats, famille, pénal, numérique, violences).",
    version=__version__,
    lifespan=cycle_de_vie,
)


# Politique de sécurité du contenu : seules les ressources du site lui-même sont chargées (aucun
# script tiers ni pisteur), la page ne peut pas être intégrée dans un autre site.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
       "font-src 'self' data:; connect-src 'self'; media-src 'self'; manifest-src 'self'; worker-src 'self'; "
       "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


@app.middleware("http")
async def sans_trace(request, suivant):
    """Aucune page ni réponse n'est gardée dans le cache du navigateur : une personne qui
    consulte l'appareil ensuite ne doit retrouver aucune copie des échanges.
    Les questions sont aussi limitées par visiteur, pour protéger le serveur contre les abus."""
    autorise, attente = limites.autoriser(limites.adresse_client(request), request.url.path)
    if not autorise:
        from fastapi.responses import JSONResponse
        texte = limites.message(request.url.path)
        reponse = JSONResponse({"detail": texte["fr"], "detail_ar": texte["ar"],
                                "reessayer_dans": attente}, status_code=429,
                               headers={"Retry-After": str(attente)})
    else:
        reponse = await suivant(request)
    reponse.headers["Cache-Control"] = "no-store"
    reponse.headers["Referrer-Policy"] = "no-referrer"
    reponse.headers["X-Content-Type-Options"] = "nosniff"
    reponse.headers["X-Frame-Options"] = "DENY"
    reponse.headers["Content-Security-Policy"] = CSP
    reponse.headers["Permissions-Policy"] = "camera=(), geolocation=(), payment=(), usb=(), interest-cohort=()"
    reponse.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        reponse.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return reponse


# --- Authentification ------------------------------------------------------

def utilisateur_courant(request: Request):
    return comptes.utilisateur_du_jeton(request.cookies.get(COOKIE))


def exiger_utilisateur(utilisateur=Depends(utilisateur_courant)):
    if utilisateur is None:
        raise HTTPException(401, "Connexion requise.")
    return utilisateur


def exiger_partenaire(utilisateur=Depends(exiger_utilisateur)):
    if utilisateur["role"] not in ("partenaire", "admin"):
        raise HTTPException(403, "Espace réservé aux associations partenaires.")
    return utilisateur


def _poser_cookie(reponse, request, jeton, rester):
    reponse.set_cookie(COOKIE, jeton, httponly=True, samesite="strict", path="/",
                       secure=request.url.scheme == "https",
                       max_age=int(comptes.DUREE_SESSION_LONGUE.total_seconds()) if rester else None)


class Inscription(BaseModel):
    pseudo: str = Field(..., max_length=30)
    mot_de_passe: str = Field(..., max_length=200)
    email: str | None = Field(None, max_length=200)
    pays: str = "TN"
    interets: list[str] = []
    langue: str = "fr"


class Connexion(BaseModel):
    identifiant: str = Field(..., max_length=200)
    mot_de_passe: str = Field(..., max_length=200)
    rester: bool = False


class Profil(BaseModel):
    pays: str | None = None
    interets: list[str] | None = None
    langue: str | None = None


@app.get("/api/auth/interets")
def interets():
    return comptes.INTERETS


@app.post("/api/auth/inscription")
def inscription(donnees: Inscription, request: Request, reponse: Response):
    try:
        comptes.inscrire(donnees.pseudo, donnees.mot_de_passe, donnees.email, donnees.pays,
                         donnees.interets, donnees.langue)
        jeton, profil = comptes.connecter(donnees.pseudo, donnees.mot_de_passe)
    except ErreurCompte as erreur:
        raise HTTPException(400, str(erreur)) from erreur
    _poser_cookie(reponse, request, jeton, False)
    return profil


@app.post("/api/auth/connexion")
def connexion_(donnees: Connexion, request: Request, reponse: Response):
    try:
        jeton, profil = comptes.connecter(donnees.identifiant, donnees.mot_de_passe, donnees.rester)
    except ErreurCompte as erreur:
        raise HTTPException(401, str(erreur)) from erreur
    _poser_cookie(reponse, request, jeton, donnees.rester)
    return profil


@app.post("/api/auth/deconnexion")
def deconnexion(request: Request, reponse: Response):
    comptes.deconnecter(request.cookies.get(COOKIE))
    reponse.delete_cookie(COOKIE, path="/")
    return {"deconnectee": True}


@app.get("/api/auth/moi")
def moi(utilisateur=Depends(utilisateur_courant)):
    return utilisateur


@app.patch("/api/auth/moi")
def modifier_moi(donnees: Profil, utilisateur=Depends(exiger_utilisateur)):
    return comptes.modifier_profil(utilisateur["id"], donnees.pays, donnees.interets, donnees.langue)


@app.delete("/api/auth/moi")
def supprimer_moi(reponse: Response, utilisateur=Depends(exiger_utilisateur)):
    comptes.supprimer(utilisateur["id"])
    reponse.delete_cookie(COOKIE, path="/")
    return {"supprime": True}


# --- Espace personnel et recommandations -----------------------------------

class Interaction(BaseModel):
    element: str = Field(..., pattern=r"^(fiche|loi):[\w\-]+$")
    action: str = Field(..., pattern=r"^(vue|favori|utile)$")


def _titre_element(element):
    r = recommandeur()
    i = r.index.get(element)
    return r.elements[i] if i is not None else None


@app.post("/api/interactions")
def interaction(donnees: Interaction, utilisateur=Depends(utilisateur_courant)):
    if utilisateur is None:
        return {"enregistre": False}  # sans compte, rien n'est gardé
    comptes.enregistrer(utilisateur["id"], donnees.element, donnees.action)
    return {"enregistre": True}


@app.delete("/api/favoris/{element}")
def retirer_favori(element: str, utilisateur=Depends(exiger_utilisateur)):
    comptes.retirer_favori(utilisateur["id"], element)
    return {"retire": True}


@app.get("/api/espace")
def espace(utilisateur=Depends(exiger_utilisateur)):
    favoris = [e for e in (_titre_element(f) for f in comptes.favoris(utilisateur["id"])) if e]
    vus = []
    for ligne in comptes.historique(utilisateur["id"], limite=60):
        e = _titre_element(ligne["element"])
        if e and e["id"] not in [v["id"] for v in vus]:
            vus.append(e)
    nettoyer = lambda e: {k: e[k] for k in ("id", "type", "titre", "pays")}  # noqa: E731
    return {"profil": utilisateur,
            "recommandations": recommandeur().recommander(utilisateur),
            "favoris": [nettoyer(e) for e in favoris],
            "recents": [nettoyer(e) for e in vus[:8]]}


# --- Conversation ----------------------------------------------------------

class Tour(BaseModel):
    role: str
    content: str


class RequeteChat(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    historique: list[Tour] = []


class RequeteTriage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class RequeteAvis(BaseModel):
    utile: bool
    # Pour l'auto-apprentissage : la clé de situation et les identifiants des sources citées.
    # Jamais le texte du message.
    cle: str | None = Field(None, max_length=80)
    sources: list[str] = Field(default_factory=list, max_length=8)
    # Signal implicite (source ouverte, réponse copiée, réponse régénérée) : poids plus faible,
    # et il n'est pas compté comme un avis dans les statistiques.
    implicite: bool = False
    poids: float = Field(1.0, ge=0.05, le=1.0)


@app.get("/api/sante")
def sante():
    return {"statut": "ok", "version": __version__, **assistant().etat(), "bibliotheque": juridique.statistiques()}


@app.post("/api/chat")
def chat(requete: RequeteChat, utilisateur=Depends(utilisateur_courant)):
    reponse = assistant().repondre(requete.message, [t.model_dump() for t in requete.historique])
    stats.message(reponse["triage"]["label"], reponse["langue"], reponse["mode"])
    if utilisateur:
        # Seuls les SUJETS (fiches et textes cités) alimentent les recommandations, jamais le message.
        for element in {s["element"] for s in reponse["sources"] if s.get("element")}:
            comptes.enregistrer(utilisateur["id"], element, "sujet")
    return reponse


@app.post("/api/chat/flux")
def chat_flux(requete: RequeteChat, utilisateur=Depends(utilisateur_courant)):
    """Réponse diffusée en direct (Server-Sent Events) : étapes, sources, texte mot à mot, fin."""
    def evenements():
        meta = None
        for evenement in assistant().repondre_flux(requete.message, [t.model_dump() for t in requete.historique]):
            if evenement["type"] == "meta":
                meta = evenement
            if evenement["type"] == "fin" and meta:
                stats.message(meta["triage"]["label"], meta["langue"], evenement["mode"])
                if utilisateur:
                    for element in {s["element"] for s in meta["sources"] if s.get("element")}:
                        comptes.enregistrer(utilisateur["id"], element, "sujet")
            yield f"data: {json.dumps(evenement, ensure_ascii=False)}\n\n"

    return StreamingResponse(evenements(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no"})


@app.post("/api/triage")
def triage(requete: RequeteTriage):
    return assistant().trieur.predire(anonymiser(requete.message))


@app.post("/api/avis")
def avis(requete: RequeteAvis):
    if not requete.implicite:
        stats.avis(requete.utile)
    appris = enregistrer_avis(requete.cle, requete.sources, requete.utile,
                              poids=requete.poids if requete.implicite else 1.0)
    return {"merci": True, "sources_apprises": appris}


# --- Analyse juridique (mode avocat) ---------------------------------------

class RequeteAnalyse(BaseModel):
    situation: str = Field(..., min_length=15, max_length=4000)
    pays: str = "TN"


@app.post("/api/analyse")
def analyse_juridique(requete: RequeteAnalyse):
    resultat = analyse.analyser(requete.situation, requete.pays, trieur=assistant().trieur)
    resultat["synthese"] = synthese_juridique(anonymiser(requete.situation), resultat)
    stats.analyse(resultat["urgence"])
    return resultat


# --- Bibliothèque juridique ------------------------------------------------

@app.get("/api/lois/pays")
def lois_pays():
    return juridique.lister_pays()


@app.get("/api/lois")
def lois(pays: str | None = None, domaine: str | None = None, type: str | None = None):
    return juridique.lister_textes(pays, domaine, type)


@app.get("/api/lois/recherche")
def lois_recherche(q: str = Query(..., min_length=2, max_length=300), pays: str | None = None):
    return juridique.rechercher(anonymiser(q), pays=pays, limite=10)


@app.get("/api/monde")
def monde():
    """Atlas : 190 pays, scores et réponses clés (Banque mondiale, WBL 2026, CC BY 4.0)."""
    return juridique.lister_monde()


@app.get("/api/monde/{code}")
def monde_pays(code: str):
    detail = juridique.detail_monde(code)
    if detail is None:
        raise HTTPException(404, "Pays introuvable.")
    return detail


@app.get("/api/lois/{texte_id}")
def loi(texte_id: str):
    texte = juridique.detail_texte(texte_id)
    if texte is None:
        raise HTTPException(404, "Texte introuvable.")
    return texte


# --- Fiches pratiques -------------------------------------------------------

@app.get("/api/fiches")
def fiches():
    """Les fiches d'information, découpées en sections."""
    sortie = []
    for fichier in sorted(DOSSIER_KB.glob("*.md")):
        sections = sections_markdown(fichier)
        if not sections:
            continue
        sortie.append({
            "id": fichier.stem,
            "titre": sections[0]["chemin"][0],
            "sections": [{"titre": s["chemin"][-1], "texte": s["texte"]}
                         for s in sections if len(s["chemin"]) > 1],
        })
    return sortie


@app.get("/api/recherche")
def recherche(q: str = Query(..., min_length=2, max_length=300), k: int = Query(5, ge=1, le=10)):
    resultats = assistant().moteur.rechercher(anonymiser(q), k=k)
    return [{"element": r["metadata"].get("element"),
             "type": r["metadata"].get("type", "fiche"),
             "fiche": r["metadata"]["source"].removesuffix(".md"),
             "titre": " > ".join(r["metadata"]["chemin"]),
             "section": r["metadata"]["chemin"][-1],
             "extrait": r["texte"].split("\n\n", 1)[-1],
             "score": round(r["score"], 3)} for r in resultats]


@app.get("/api/ressources")
def ressources():
    return json.loads((RACINE / "data" / "ressources.json").read_text(encoding="utf-8"))


# --- Évaluation du danger --------------------------------------------------

class RequeteRisque(BaseModel):
    reponses: dict[str, bool]
    langue: str = "fr"


@app.get("/api/risque/questions")
def risque_questions(langue: str = "fr"):
    return risque.questions(langue)


@app.post("/api/risque")
def risque_evaluer(requete: RequeteRisque):
    inconnues = set(requete.reponses) - set(risque.QUESTIONS_ORDONNEES)
    if inconnues:
        raise HTTPException(422, f"Questions inconnues : {sorted(inconnues)}")
    resultat = risque.evaluer(requete.reponses, requete.langue)
    stats.evaluation_risque(resultat["niveau"])
    return resultat


# --- Espace partenaires (réservé) ------------------------------------------

@app.get("/api/statistiques")
def statistiques(_partenaire=Depends(exiger_partenaire)):
    evaluation = None
    if RAPPORT_EVALUATION.exists():
        evaluation = json.loads(RAPPORT_EVALUATION.read_text(encoding="utf-8"))
        evaluation.pop("triage_erreurs", None)  # contient des exemples de texte : non exposé
    return {"usage": stats.resume(), "systeme": assistant().etat(), "bibliotheque": juridique.statistiques(),
            "apprentissage": bilan_apprentissage(), "veille": veille.etat,
            "fiches": len(list(DOSSIER_KB.glob("*.md"))), "evaluation": evaluation}


@app.get("/api/sources-externes")
def sources_externes(statut: str = "a_verifier", _partenaire=Depends(exiger_partenaire)):
    """Pistes trouvées en ligne par la recherche externe, à relire par un partenaire juriste."""
    from . import recherche_externe
    cnx = recherche_externe.connexion()
    cnx.executescript(recherche_externe.SCHEMA)
    lignes = cnx.execute("SELECT id, requete, url, titre, extrait, site, statut, trouve_le, vu FROM sources_externes "
                         "WHERE statut = ? ORDER BY vu DESC, trouve_le DESC LIMIT 200", (statut,)).fetchall()
    return [dict(l) for l in lignes]


class DecisionSource(BaseModel):
    statut: str


@app.post("/api/sources-externes/{identifiant}")
def valider_source_externe(identifiant: int, decision: DecisionSource, _partenaire=Depends(exiger_partenaire)):
    """Valider (la piste est montrée en premier) ou rejeter (elle n'est plus jamais proposée)."""
    if decision.statut not in ("valide", "rejete", "a_verifier"):
        raise HTTPException(400, "Statut attendu : valide, rejete ou a_verifier.")
    from . import recherche_externe
    cnx = recherche_externe.connexion()
    cnx.executescript(recherche_externe.SCHEMA)
    if not cnx.execute("UPDATE sources_externes SET statut = ? WHERE id = ?", (decision.statut, identifiant)).rowcount:
        raise HTTPException(404, "Source inconnue.")
    cnx.commit()
    return {"id": identifiant, "statut": decision.statut}


# --- Interface --------------------------------------------------------------

app.mount("/static", StaticFiles(directory=DOSSIER_WEB), name="static")


# Version mobile (application installable, dossier mobile/) : même API, même base juridique.
@app.get("/mobile", include_in_schema=False)
def mobile_sans_barre():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/mobile/")


@app.get("/.well-known/assetlinks.json", include_in_schema=False)
def liens_android():
    """Lien entre le site et l'application Android (TWA) : sans ce fichier, Android afficherait une
    barre d'adresse. Rempli avec l'empreinte SHA-256 de la clé de signature du paquet Play Store."""
    fichier = RACINE / "mobile" / "assetlinks.json"
    if not fichier.exists():
        raise HTTPException(404, "Aucune application Android liée.")
    return json.loads(fichier.read_text(encoding="utf-8"))


if (RACINE / "mobile").exists():
    app.mount("/mobile", StaticFiles(directory=RACINE / "mobile", html=True), name="mobile")


@app.get("/")
def accueil():
    return FileResponse(DOSSIER_WEB / "index.html")
