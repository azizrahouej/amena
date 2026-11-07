"""Comptes utilisatrices : inscription, connexion, sessions, suppression.

Sécurité :
    - mots de passe hachés avec PBKDF2-HMAC-SHA256 (sel aléatoire, 310 000 itérations) ;
    - jetons de session aléatoires (256 bits), seul leur HACHÉ est stocké en base ;
    - limitation des tentatives de connexion (anti force brute) ;
    - un pseudonyme suffit : l'e-mail est facultatif.

Confidentialité : un compte est FACULTATIF. Tout le site fonctionne sans compte. Le compte sert
uniquement à retrouver ses favoris et des recommandations ; aucun message n'y est enregistré.
"""

import hashlib
import hmac
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .base import connexion, lignes

ITERATIONS = 310_000
DUREE_SESSION = timedelta(hours=12)
DUREE_SESSION_LONGUE = timedelta(days=14)
INTERETS = ["violence conjugale", "violence sexuelle", "violence économique", "harcèlement",
            "harcèlement en ligne", "divorce", "garde des enfants", "pension alimentaire",
            "procédure", "protection", "travail", "droits fondamentaux"]

_tentatives = defaultdict(list)


class ErreurCompte(Exception):
    """Erreur présentée telle quelle à l'utilisatrice."""


# --- Mots de passe ---------------------------------------------------------

def hacher(mot_de_passe):
    sel = secrets.token_bytes(16)
    empreinte = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), sel, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${sel.hex()}${empreinte.hex()}"


def verifier(mot_de_passe, stocke):
    try:
        _, iterations, sel, empreinte = stocke.split("$")
    except ValueError:
        return False
    calcul = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), bytes.fromhex(sel), int(iterations))
    return hmac.compare_digest(calcul.hex(), empreinte)  # comparaison à temps constant


def _hacher_jeton(jeton):
    return hashlib.sha256(jeton.encode()).hexdigest()


# --- Inscription et connexion ----------------------------------------------

def inscrire(pseudo, mot_de_passe, email=None, pays="TN", interets=(), langue="fr", role="utilisatrice", cnx=None):
    cnx = cnx or connexion()
    pseudo = (pseudo or "").strip()
    if not re.fullmatch(r"[\w.\-]{3,30}", pseudo):
        raise ErreurCompte("Le pseudonyme doit faire 3 à 30 caractères (lettres, chiffres, . - _).")
    if len(mot_de_passe or "") < 8:
        raise ErreurCompte("Le mot de passe doit faire au moins 8 caractères.")
    email = (email or "").strip() or None
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ErreurCompte("Adresse e-mail invalide.")
    interets = [i for i in interets if i in INTERETS]
    try:
        with cnx:
            curseur = cnx.execute(
                "INSERT INTO utilisateurs (pseudo, email, hash_mdp, role, langue, pays, interets) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pseudo, email, hacher(mot_de_passe), role, langue, pays, ",".join(interets)))
    except Exception as erreur:
        if "UNIQUE" in str(erreur):
            raise ErreurCompte("Ce pseudonyme ou cet e-mail est déjà utilisé.") from erreur
        raise
    return curseur.lastrowid


def connecter(identifiant, mot_de_passe, rester=False, cnx=None):
    """Renvoie (jeton, utilisateur). Le jeton n'est connu que du navigateur."""
    cnx = cnx or connexion()
    cle = (identifiant or "").strip().lower()
    maintenant = time.time()
    _tentatives[cle] = [t for t in _tentatives[cle] if maintenant - t < 900]
    if len(_tentatives[cle]) >= 5:
        raise ErreurCompte("Trop de tentatives. Réessayez dans 15 minutes.")

    ligne = cnx.execute("SELECT * FROM utilisateurs WHERE pseudo = ? OR email = ?", (cle, cle)).fetchone()
    if ligne is None or not verifier(mot_de_passe or "", ligne["hash_mdp"]):
        _tentatives[cle].append(maintenant)
        # Message volontairement identique dans les deux cas : on ne révèle pas si le compte existe.
        raise ErreurCompte("Identifiant ou mot de passe incorrect.")
    _tentatives.pop(cle, None)

    jeton = secrets.token_urlsafe(32)
    expire = datetime.now(timezone.utc) + (DUREE_SESSION_LONGUE if rester else DUREE_SESSION)
    with cnx:
        cnx.execute("DELETE FROM sessions WHERE expire_le < ?", (datetime.now(timezone.utc).isoformat(),))
        cnx.execute("INSERT INTO sessions VALUES (?, ?, ?)", (_hacher_jeton(jeton), ligne["id"], expire.isoformat()))
    return jeton, profil(ligne["id"], cnx)


def utilisateur_du_jeton(jeton, cnx=None):
    if not jeton:
        return None
    cnx = cnx or connexion()
    ligne = cnx.execute("""SELECT u.id FROM sessions s JOIN utilisateurs u ON u.id = s.utilisateur_id
                           WHERE s.jeton_hash = ? AND s.expire_le > ?""",
                        (_hacher_jeton(jeton), datetime.now(timezone.utc).isoformat())).fetchone()
    return profil(ligne["id"], cnx) if ligne else None


def deconnecter(jeton, cnx=None):
    if jeton:
        cnx = cnx or connexion()
        with cnx:
            cnx.execute("DELETE FROM sessions WHERE jeton_hash = ?", (_hacher_jeton(jeton),))


def profil(utilisateur_id, cnx=None):
    cnx = cnx or connexion()
    ligne = cnx.execute("SELECT id, pseudo, email, role, langue, pays, interets, cree_le FROM utilisateurs WHERE id = ?",
                        (utilisateur_id,)).fetchone()
    if ligne is None:
        return None
    p = dict(ligne)
    p["interets"] = [i for i in (p["interets"] or "").split(",") if i]
    return p


def modifier_profil(utilisateur_id, pays=None, interets=None, langue=None, cnx=None):
    cnx = cnx or connexion()
    with cnx:
        if pays:
            cnx.execute("UPDATE utilisateurs SET pays = ? WHERE id = ?", (pays, utilisateur_id))
        if interets is not None:
            cnx.execute("UPDATE utilisateurs SET interets = ? WHERE id = ?",
                        (",".join(i for i in interets if i in INTERETS), utilisateur_id))
        if langue in ("fr", "ar"):
            cnx.execute("UPDATE utilisateurs SET langue = ? WHERE id = ?", (langue, utilisateur_id))
    return profil(utilisateur_id, cnx)


def supprimer(utilisateur_id, cnx=None):
    """Droit à l'effacement : compte, sessions et interactions disparaissent (ON DELETE CASCADE)."""
    cnx = cnx or connexion()
    with cnx:
        cnx.execute("DELETE FROM utilisateurs WHERE id = ?", (utilisateur_id,))


# --- Interactions et favoris -----------------------------------------------

POIDS = {"vue": 1.0, "sujet": 1.5, "utile": 2.0, "favori": 3.0}


def enregistrer(utilisateur_id, element, action, cnx=None):
    cnx = cnx or connexion()
    with cnx:
        if action == "favori" and cnx.execute(
                "SELECT 1 FROM interactions WHERE utilisateur_id = ? AND element = ? AND action = 'favori'",
                (utilisateur_id, element)).fetchone():
            return
        cnx.execute("INSERT INTO interactions (utilisateur_id, element, action, poids) VALUES (?, ?, ?, ?)",
                    (utilisateur_id, element, action, POIDS[action]))


def retirer_favori(utilisateur_id, element, cnx=None):
    cnx = cnx or connexion()
    with cnx:
        cnx.execute("DELETE FROM interactions WHERE utilisateur_id = ? AND element = ? AND action = 'favori'",
                    (utilisateur_id, element))


def favoris(utilisateur_id, cnx=None):
    cnx = cnx or connexion()
    return [r["element"] for r in cnx.execute(
        "SELECT element FROM interactions WHERE utilisateur_id = ? AND action = 'favori' ORDER BY id DESC",
        (utilisateur_id,))]


def historique(utilisateur_id, limite=50, cnx=None):
    cnx = cnx or connexion()
    return lignes(cnx.execute("""SELECT element, action, poids, cree_le FROM interactions
                                 WHERE utilisateur_id = ? ORDER BY id DESC LIMIT ?""", (utilisateur_id, limite)))


def toutes_interactions(cnx=None):
    cnx = cnx or connexion()
    return lignes(cnx.execute("SELECT utilisateur_id, element, SUM(poids) AS poids FROM interactions GROUP BY 1, 2"))
