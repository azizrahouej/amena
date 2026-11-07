"""Orchestrateur : relie sécurité, triage, recherche et génération.

    message brut
        -> anonymisation      (aucune donnée identifiante ne sort du serveur)
        -> détection langue
        -> triage             (urgence / juridique / soutien / information)
        -> recherche          (passages de la base de connaissances)
        -> génération         (LLM ou extractif)
        -> réponse + sources + niveau d'alerte

Aucune conversation n'est enregistrée côté serveur : l'historique reste dans le
navigateur de l'utilisatrice et disparaît avec le bouton « Sortie rapide ».
"""

from . import juridique
from .config import FICHIER_CHUNKS, INDEX_RECHERCHE, MODELE_TRIAGE
import re

from . import recherche_externe
from .analyse import BASE_EXPERTISE, SITUATIONS_CIVILES, analyser
from .apprentissage import cle_apprentissage, identifiant, reclasser
from .conversation import contextualiser, petite_discussion, suggestions
from .securite import regles_danger
from .config import MODELE_LLM
from .generation import CLOUD_MODELE, OLLAMA_MODELE, fournisseur, generer, generer_flux
from .recherche import MoteurRecherche
from .securite import anonymiser, detecter_langue, normaliser
from .triage import Trieur

CONTACTS_URGENCE = [
    {"numero": "197", "nom": "Police secours"},
    {"numero": "193", "nom": "Garde nationale"},
    {"numero": "190", "nom": "SAMU"},
    {"numero": "1899", "nom": "Numéro vert violences faites aux femmes (gratuit)"},
]

_PERSONNEL = re.compile(r"(\bje\b|\bj'|\bj\s|\bmon\b|\bma\b|\bmes\b|\bmoi\b|\bm'|\bena\b|\b3andi\b|\bandi\b|"
                        r"\bn7eb\b|\bnheb\b|\bliya\b|\blia\b|\bna3mel\b|أنا|انا|عندي|ليا|نعمل|بابا|امي|أبي|ابي)")


# Vocabulaire des questions de droit civil (texte normalisé : sans accents, ة→ه, أ→ا).
_QUESTION_CIVILE = re.compile(
    r"herit|succession|testament|divorc|pension|garde des enfants|contrat|loyer|locat|bail|salaire|licenci|"
    r"terrain|propriet|achat|vente|vendeur|acheteur|dette|credit|banque|impot|notaire|"
    r"ارث|ميراث|ورث|التركه|وصيه|طلاق|نفقه|حضانه|عقد|كراء|اجر|ارض|عقار|بيع|شراء|دين|بنك|عدل|"
    r"werth|wirth|tarka|tla9|kra|chhriya|ardh|bi3|dyoun|flous")


def _lien(meta):
    """Lien de l'interface vers la source : fiche pratique ou texte de loi."""
    element = meta.get("element") or ""
    if meta.get("type") == "monde":
        return f"#/monde/{meta['source'][6:]}"
    if element.startswith("loi:"):
        return f"#/lois/{element[4:]}"
    return f"#/droits/{meta['source'].removesuffix('.md')}"


class Assistant:
    def __init__(self, trieur, moteur):
        self.trieur = trieur
        self.moteur = moteur

    @classmethod
    def charger(cls):
        """Charge les modèles ; les construit automatiquement s'ils n'existent pas encore."""
        from .base import FICHIER_BASE
        if not all(f.exists() for f in (MODELE_TRIAGE, INDEX_RECHERCHE, FICHIER_CHUNKS, FICHIER_BASE)):
            from .construction import tout_construire
            tout_construire(verbeux=False)
        return cls(Trieur.charger(), MoteurRecherche.charger())

    def preparer(self, message, historique=None):
        """Tout ce qui précède la rédaction : anonymisation, langue, triage, recherche."""
        message = (message or "").strip()[:2000]
        texte = anonymiser(message)
        historique = [{**t, "content": anonymiser(t.get("content", ""))} for t in (historique or [])]
        langue = detecter_langue(texte)
        # Une relance courte (« et au Maroc ? ») est comprise avec le sujet du message précédent :
        # seule, elle serait mal classée et mal recherchée.
        requete = contextualiser(texte, historique)
        triage = self.trieur.predire(requete)
        if (triage["label"] == "urgence" and not regles_danger(texte)
                and triage["probabilites"].get("urgence", 0) < 0.5 and _QUESTION_CIVILE.search(normaliser(texte))):
            # Question de droit civil (héritage, divorce, contrat, loyer…) sans aucun mot de danger : le
            # classifieur hésitait (moins de 50 %), ce n'est pas une urgence. Les règles de danger restent
            # prioritaires : « mon frère me menace pour l'héritage » reste une urgence.
            triage = {**triage, "label": "juridique", "raison": "question_civile"}
        urgence = triage["label"] == "urgence"
        sources = self.moteur.rechercher(requete)
        # Un pays est cité ? On ajoute la fiche Banque mondiale de ce pays (190 pays couverts).
        iso3 = None if urgence else juridique.detecter_pays(texte)
        if iso3:
            resume = juridique.resume_monde(iso3)
            if resume:
                nom = resume.split(",", 1)[0]
                fiche_monde = {"id": f"monde_{iso3}", "texte": f"{nom} > Banque mondiale (WBL 2026)\n\n{resume}",
                               "score": 1.0, "metadata": {"source": f"monde:{iso3}", "type": "monde",
                                                          "element": None, "chemin": [nom, "Banque mondiale (WBL 2026)"]}}
                if iso3 != "TUN":
                    # Question sur un autre pays : on écarte les fiches et lois TUNISIENNES, qui
                    # induiraient en erreur ; on garde les textes de ce pays et l'international.
                    from .donnees_wbl import ISO2_VERS_ISO3
                    iso2 = next((k for k, v in ISO2_VERS_ISO3.items() if v == iso3), "ZZ")
                    sources = self.moteur.rechercher(requete, k=3, types={"loi"}, pays=iso2)
                sources = [fiche_monde] + sources[:3]
        # Consultation « avocate » : si le message décrit une situation reconnue par la base
        # d'expertise, les articles qui la fondent deviennent les premières sources citées.
        expertise = None
        if not iso3 or iso3 == "TUN":
            # Une situation personnelle (« j'ai », « mon », « 3andi », « عندي »…) reçoit toujours une
            # consultation structurée, même hors des cas connus : la méthode et des questions pour préciser.
            personnel = bool(_PERSONNEL.search(f" {texte.lower()} ")) and triage["label"] != "information"
            analyse_situation = analyser(requete, "TN", generale=personnel)
            analyse_situation = self._suite_de_consultation(analyse_situation, texte, historique, personnel)
            if analyse_situation["qualifications"]:
                # Situation civile (argent, terre, contrat) sans règle de danger : c'est une question
                # juridique, pas une urgence ni une demande d'écoute, quoi qu'en dise le classifieur.
                civile = all(q["id"] in SITUATIONS_CIVILES for q in analyse_situation["qualifications"])
                if civile and not regles_danger(texte):
                    urgence = False
                    triage = {**triage, "label": "juridique"}
                    if analyse_situation.get("generale"):
                        # Situation inconnue : les articles des codes officiels les plus proches de la
                        # question servent d'appui au modèle (il ne peut citer que ceux-là).
                        sources = [s for s in self.moteur.rechercher(requete, k=15)
                                   if str(s["metadata"].get("element", "")).startswith("loi:tn-off-")][:5]
                    elif not any(q["fondements"] for q in analyse_situation["qualifications"]):
                        sources = []  # pas de texte dans la base : on n'affiche pas de sources hors sujet
                analyse_situation["urgence"] = urgence or analyse_situation["urgence"]
                expertise = analyse_situation
                fondements = self._chunks_fondements(expertise)
                ids = {c["id"] for c in fondements}
                autres = [s for s in sources if s["id"] not in ids]
                if civile:
                    # Hors violences, les fiches et lois étrangères de la base seraient hors sujet :
                    # on ne garde que les codes officiels tunisiens.
                    autres = [s for s in autres if str(s["metadata"].get("element", "")).startswith("loi:tn-off-")]
                    autres = autres[:5] if analyse_situation.get("generale") else autres[:2]
                sources = (fondements + autres)[:6]
        if urgence:
            # En urgence, la fiche de mise en sécurité passe en premier, devant les
            # définitions juridiques.
            securite = self.moteur.rechercher("se mettre en sécurité danger immédiat appeler", k=1)
            ids = {s["id"] for s in securite}
            sources = (securite + [s for s in sources if s["id"] not in ids])[:max(len(sources), 1)]
        sources = reclasser(sources, cle_apprentissage(triage, expertise))
        from .generation import _deja_traitee
        # Ce que la base ne couvre pas (situation inconnue ou aucune source) : pistes en ligne, sur des
        # sites juridiques fiables, à partir de mots-clés seulement (voir recherche_externe.py).
        pistes = []
        if not urgence and (not sources or (expertise and expertise.get("generale"))):
            pistes = recherche_externe.rechercher(texte)
        return {"message": message, "texte": texte, "historique": historique, "langue": langue,
                "triage": triage, "urgence": urgence, "sources": sources, "expertise": expertise,
                "suite": _deja_traitee(expertise, historique), "pistes": pistes}

    @staticmethod
    def _suite_de_consultation(analyse_courante, texte, historique, personnel):
        """Dans une conversation, une précision (« il a pris 3000 dinars de mon compte ») se comprend
        avec le message précédent : on garde la situation déjà identifiée tant que le nouveau message
        n'en décrit pas une autre."""
        precedents = [t["content"] for t in historique or [] if t.get("role") == "user" and t.get("content")]
        if not precedents:
            return analyse_courante
        ensemble = analyser(f"{precedents[-1]} {texte}", "TN", generale=personnel)
        if not ensemble["qualifications"] or ensemble.get("generale"):
            return analyse_courante
        couvertes = {q["id"] for q in ensemble["qualifications"]}
        couvertes |= {r for q in ensemble["qualifications"]
                      for s in BASE_EXPERTISE["situations"] if s["id"] == q["id"] for r in s.get("remplace", [])}
        courantes = {q["id"] for q in analyse_courante["qualifications"]} - {"generale"}
        return ensemble if courantes <= couvertes else analyse_courante

    def _chunks_fondements(self, expertise):
        """Les passages de l'index qui correspondent aux articles invoqués par l'analyse."""
        trouves = []
        for q in expertise["qualifications"]:
            for f in q["fondements"]:
                for c in self.moteur.chunks:
                    chemin = c["metadata"].get("chemin", [])
                    if (c["metadata"].get("element") == f"loi:{f['texte_id']}" and chemin
                            and chemin[-1].startswith(f"Art. {f['article']}") and c not in trouves):
                        trouves.append({**c, "score": 1.0})
                        break
        return trouves[:4]

    @staticmethod
    def _reponses_rapides(ctx):
        """Les réponses rapides de la situation que la personne n'a pas encore utilisées."""
        deja = {(t.get("content") or "").strip() for t in ctx.get("historique") or [] if t.get("role") == "user"}
        deja.add(ctx["message"].strip())
        reponses = [r for r in ((ctx.get("expertise") or {}).get("reponses") or []) if r not in deja]
        return reponses[:3] if ctx.get("suite") else reponses

    def _meta(self, ctx):
        """Ce que l'interface affiche avant même que la réponse soit rédigée."""
        return {
            "langue": ctx["langue"],
            "urgence": ctx["urgence"],
            "triage": ctx["triage"],
            "contacts": CONTACTS_URGENCE if ctx["urgence"] else CONTACTS_URGENCE[-1:],
            "sources": [{
                "fichier": s["metadata"]["source"],
                "type": s["metadata"].get("type", "fiche"),
                "element": s["metadata"].get("element"),
                "lien": _lien(s["metadata"]),
                "titre": " > ".join(s["metadata"]["chemin"]),
                "extrait": s["texte"].split("\n\n", 1)[-1][:280],
                "score": round(s["score"], 3),
                "id_apprentissage": identifiant(s),
            } for s in ctx["sources"]],
            # Réponses rapides propres à la situation (« Je n'ai pas de titre foncier »…) pour la préciser
            # en un clic ; sinon les questions de suivi habituelles.
            "suggestions": self._reponses_rapides(ctx) or suggestions(ctx["triage"], ctx["sources"], ctx["langue"]),
            # La situation a été précisée : on propose de préparer le PDF pour l'avocat(e).
            "proposer_dossier": bool(ctx.get("suite")),
            "pistes_externes": ctx.get("pistes", []),
            "message_anonymise": ctx["texte"] != ctx["message"],
            # Repris par la page « Dossier pour mon avocat(e) » ; aucun texte n'est stocké côté serveur.
            "expertise": ({"situations": [q["libelle"] for q in ctx["expertise"]["qualifications"]],
                           "analyse": {k: ctx["expertise"][k] for k in ("qualifications", "demarches", "preuves",
                                                                        "delais", "vigilance", "limites_loi")}}
                          if ctx.get("expertise") else None),
            "cle_apprentissage": cle_apprentissage(ctx["triage"], ctx.get("expertise")),
        }

    def _petite(self, ctx):
        """Salutation, remerciement… : réponse directe, sans recherche ni sources."""
        # Un « bonjour » isolé peut être mal classé par le modèle : seule une vraie règle de
        # danger (menace, arme, « au secours »...) empêche la réponse de courtoisie.
        if regles_danger(ctx["texte"]):
            return None
        reponse = petite_discussion(ctx["texte"], ctx["langue"])
        if reponse:
            ctx["sources"] = []
            ctx["expertise"] = None
            ctx["urgence"] = False
            ctx["triage"] = {**ctx["triage"], "label": "information"}
        return reponse

    def repondre(self, message, historique=None):
        ctx = self.preparer(message, historique)
        petite = self._petite(ctx)
        if petite:
            return {"reponse": petite, "mode": "conversation", **self._meta(ctx)}
        reponse, mode = generer(ctx["texte"], ctx["sources"], ctx["triage"], ctx["langue"], ctx["historique"],
                                expertise=ctx["expertise"], pistes=ctx["pistes"])
        reponse += recherche_externe.bloc_reponse(ctx["pistes"], ctx["langue"])
        return {"reponse": reponse, "mode": mode, **self._meta(ctx)}

    def repondre_flux(self, message, historique=None):
        """Version diffusée : événements « etape », « meta », « texte » puis « fin »."""
        yield {"type": "etape", "cle": "analyse"}
        ctx = self.preparer(message, historique)
        petite = self._petite(ctx)
        if petite:
            yield {"type": "meta", **self._meta(ctx)}
            for morceau in re.findall(r"\S+\s*", petite):
                yield {"type": "texte", "delta": morceau}
            yield {"type": "fin", "mode": "conversation", "reponse": petite}
            return
        meta = self._meta(ctx)
        yield {"type": "etape", "cle": "sources", "nombre": len(ctx["sources"])}
        yield {"type": "meta", **meta}
        yield {"type": "etape", "cle": "redaction"}
        morceaux, mode = [], "extractif"
        for genre, valeur in generer_flux(ctx["texte"], ctx["sources"], ctx["triage"], ctx["langue"], ctx["historique"],
                                          expertise=ctx["expertise"], pistes=ctx["pistes"]):
            if genre == "texte":
                morceaux.append(valeur)
                yield {"type": "texte", "delta": valeur}
            else:
                mode = valeur
        bloc = recherche_externe.bloc_reponse(ctx["pistes"], ctx["langue"])
        if bloc:
            morceaux.append(bloc)
            yield {"type": "texte", "delta": bloc}
        yield {"type": "fin", "mode": mode, "reponse": "".join(morceaux).strip()}

    def etat(self):
        choix = fournisseur()
        return {"llm": choix is not None, "moteur": choix or "extractif",
                "modele": {"claude": MODELE_LLM, "cloud": CLOUD_MODELE, "ollama": OLLAMA_MODELE}.get(choix),
                "chunks": len(self.moteur.chunks), "embeddings": self.moteur.encodeur is not None}
