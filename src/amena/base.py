"""Base de données SQLite d'AMENA (bibliothèque juridique, comptes, interactions).

SQLite est inclus dans Python : aucun serveur à installer, un seul fichier, et la recherche
plein texte FTS5 (classement BM25) est intégrée.
"""

import os
import sqlite3
import threading
from pathlib import Path

from .config import RACINE

FICHIER_BASE = Path(os.getenv("AMENA_BASE", RACINE / "data" / "amena.db"))

SCHEMA = """
PRAGMA foreign_keys = ON;

-- Bibliothèque juridique ----------------------------------------------------
CREATE TABLE IF NOT EXISTS pays (
    code TEXT PRIMARY KEY, nom_fr TEXT NOT NULL, nom_ar TEXT, region TEXT
);
CREATE TABLE IF NOT EXISTS textes (
    id TEXT PRIMARY KEY,
    pays TEXT NOT NULL REFERENCES pays(code),
    type TEXT, titre TEXT NOT NULL, reference TEXT, date TEXT,
    domaines TEXT, source TEXT, url TEXT, resume TEXT
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texte_id TEXT NOT NULL REFERENCES textes(id) ON DELETE CASCADE,
    numero TEXT, titre TEXT, contenu TEXT NOT NULL, position INTEGER
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    texte_id TEXT NOT NULL REFERENCES textes(id) ON DELETE CASCADE,
    type TEXT CHECK (type IN ('force', 'lacune', 'vigilance')),
    contenu TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
    titre_texte, numero, titre, contenu,
    content='', tokenize='unicode61 remove_diacritics 2'
);

-- Données mondiales (Banque mondiale, WBL 2026) ------------------------------
CREATE TABLE IF NOT EXISTS monde_pays (
    iso3 TEXT PRIMARY KEY, pays_fr TEXT NOT NULL, pays_en TEXT, region_fr TEXT, revenu TEXT, annee INTEGER,
    score_cadre_legal REAL, score_dispositifs REAL, score_application REAL,
    sous_mariage_enfants REAL, sous_harcelement REAL, sous_violence_domestique REAL, sous_feminicide REAL
);
CREATE TABLE IF NOT EXISTS monde_indicateurs (
    iso3 TEXT NOT NULL REFERENCES monde_pays(iso3) ON DELETE CASCADE,
    code TEXT NOT NULL, pilier TEXT, theme TEXT, question TEXT, reponse INTEGER, base_legale TEXT,
    PRIMARY KEY (iso3, code)
);

-- Comptes -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS utilisateurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pseudo TEXT NOT NULL UNIQUE COLLATE NOCASE,
    email TEXT UNIQUE COLLATE NOCASE,
    hash_mdp TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'utilisatrice' CHECK (role IN ('utilisatrice', 'partenaire', 'admin')),
    langue TEXT DEFAULT 'fr',
    pays TEXT DEFAULT 'TN',
    interets TEXT DEFAULT '',
    cree_le TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessions (
    jeton_hash TEXT PRIMARY KEY,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    expire_le TEXT NOT NULL
);

-- Interactions (pour les recommandations) : jamais de texte de message ---------
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    utilisateur_id INTEGER NOT NULL REFERENCES utilisateurs(id) ON DELETE CASCADE,
    element TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('vue', 'favori', 'utile', 'sujet')),
    poids REAL NOT NULL DEFAULT 1,
    cree_le TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_interactions_utilisateur ON interactions(utilisateur_id);
CREATE INDEX IF NOT EXISTS idx_interactions_element ON interactions(element);
"""

_local = threading.local()


def connexion(chemin=None):
    """Une connexion par fil d'exécution (FastAPI sert les requêtes en parallèle)."""
    chemin = Path(chemin or FICHIER_BASE)
    cle = f"cnx_{chemin}"
    cnx = getattr(_local, cle, None)
    if cnx is None:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        cnx = sqlite3.connect(chemin, check_same_thread=False)
        cnx.row_factory = sqlite3.Row
        cnx.execute("PRAGMA foreign_keys = ON")
        cnx.execute("PRAGMA journal_mode = WAL")
        cnx.executescript(SCHEMA)
        setattr(_local, cle, cnx)
    return cnx


def lignes(curseur):
    return [dict(ligne) for ligne in curseur.fetchall()]
