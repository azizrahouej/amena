"""Génération de la réponse (le « G » de RAG).

Trois modes, choisis automatiquement (variable AMENA_LLM = auto | claude | ollama | aucun) :
    - « llm »        : Claude (API Anthropic) si ANTHROPIC_API_KEY est définie ;
    - « llm-local »  : un modèle open source qui tourne SUR CET ORDINATEUR via Ollama
                       (par défaut llama3.2:3b) : gratuit, et aucune donnée ne sort de la machine ;
    - « extractif »  : sans modèle, la réponse est composée à partir des sources.
Les deux premiers rédigent une réponse conversationnelle à partir des SEULS passages récupérés,
diffusée mot à mot. Le message est ANONYMISÉ avant tout envoi, et chaque affirmation renvoie à
sa source par une citation [n].
"""

import os
import re
import threading
import time

import httpx

from .config import MODELE_LLM

CHOIX_LLM = os.getenv("AMENA_LLM", "auto").lower()
OLLAMA_URL = os.getenv("AMENA_OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODELE = os.getenv("AMENA_OLLAMA_MODELE", "llama3.2:3b")
LANGUES = {"fr": "français", "ar": "arabe standard", "dz": "dialecte tunisien écrit en lettres latines (arabizi)"}
_cache_ollama = {"quand": 0.0, "ok": False}
from .conversation import composer
from .recherche import phrases_pertinentes

CONSIGNES_SYSTEME = """Tu es AMENA, une assistante juridique (avocate numérique) qui aide toute personne \
en Tunisie à comprendre ses droits et à agir : travail, contrats, famille, pénal, numérique, violences. \
Tu converses comme une professionnelle attentive : chaleureuse, précise, jamais condescendante. \
La personne peut être inquiète ou en détresse.

Règles de fond :
- Appuie-toi UNIQUEMENT sur les extraits fournis entre balises <sources>. Cite chaque affirmation \
juridique avec le numéro de sa source entre crochets, par exemple [2]. Si l'information n'y figure pas, \
dis-le franchement et oriente vers un avocat, une maison du droit ou, en cas de violence, le numéro vert 1899.
- Réponds dans la langue de la personne : français, arabe, ou dialecte tunisien (en lettres latines \
si elle écrit ainsi). Adresse-toi à elle sans supposer son genre.
- Ne pose jamais de diagnostic médical ou psychologique et ne garantis aucune issue judiciaire ; \
précise si utile qu'un avocat ou une association peut confirmer.
- Danger immédiat ou idées suicidaires : commence par les numéros 197 (police), 193 (garde nationale), \
190 (SAMU) et 1899 (numéro vert), en gras.

Forme, comme une avocate qui reçoit un client ou une cliente :
- Commence par une phrase qui accueille ce que la personne a dit, sans formule toute faite.
- Si une <analyse_experte> est fournie, suis cette structure avec des titres « ### » :
  Ce que je comprends de votre situation ; Ce que dit la loi (articles, cités [n]) ;
  Les étapes à suivre, dans l'ordre (liste numérotée, chaque étape concrète : où aller, quoi demander) ;
  Les preuves à réunir ; Ce qu'il faut savoir (délais, points faibles du dossier, limites de la loi) ;
  Mon conseil (la priorité, en une ou deux phrases).
- Sinon, structure librement avec des titres courts, des listes et du **gras** pour l'essentiel.
- Sois concrète : qui contacter, quel document demander, dans quel ordre.
- Termine par UNE question de relance ; si une situation est analysée, propose de préparer le dossier \
à remettre à son avocat(e).
- 380 mots maximum."""

CONCLUSION_EXTRACTIF = {
    "fr": "Pour un avis personnalisé, un(e) avocat(e) ou l'aide juridictionnelle peut vous accompagner ; en cas de violence, le **1899** est gratuit.",
    "dz": "Tnajem tchouf avocat walla l'aide juridictionnelle ; w ken famma 3onf, el **1899** bilech.",
    "ar": "لرأي شخصي يمكنك استشارة محام أو طلب الإعانة العدلية، وفي حالة العنف الرقم الأخضر **1899** مجاني.",
}


def ollama_disponible():
    """Le serveur Ollama répond-il, et le modèle est-il installé ? (vérifié toutes les 30 s)"""
    if time.time() - _cache_ollama["quand"] < 30:
        return _cache_ollama["ok"]
    try:
        modeles = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=2).json().get("models", [])
        ok = any(m.get("name") == OLLAMA_MODELE or m.get("model") == OLLAMA_MODELE for m in modeles)
    except (httpx.HTTPError, ValueError):
        ok = False
    _cache_ollama.update(quand=time.time(), ok=ok)
    return ok


def _cle_cloud():
    return os.getenv("AMENA_LLM_API_KEY") or os.getenv("GROQ_API_KEY")


def fournisseur():
    """« claude », « cloud » (API compatible OpenAI : Groq, Gemini, OpenRouter… gratuite),
    « ollama » ou None (mode extractif)."""
    if CHOIX_LLM == "aucun":
        return None
    if CHOIX_LLM in ("auto", "claude") and os.getenv("ANTHROPIC_API_KEY"):
        return "claude"
    if CHOIX_LLM in ("auto", "claude", "cloud") and _cle_cloud():
        return "cloud"
    if CHOIX_LLM in ("auto", "ollama") and ollama_disponible():
        return "ollama"
    return None


# --- Modèle en ligne gratuit (API compatible OpenAI) -------------------------------------------------
# Par défaut Groq (llama-3.3-70b, offre gratuite sans carte bancaire). Pour Gemini :
#   AMENA_LLM_URL=https://generativelanguage.googleapis.com/v1beta/openai  AMENA_LLM_MODELE=gemini-2.5-flash
CLOUD_URL = os.getenv("AMENA_LLM_URL", "https://api.groq.com/openai/v1").rstrip("/")
CLOUD_MODELE = os.getenv("AMENA_LLM_MODELE", "llama-3.3-70b-versatile")


def _flux_cloud(systeme, messages, max_tokens=1600, temperature=0.3):
    """Diffuse la réponse d'une API compatible OpenAI (événements SSE « data: … »)."""
    import json as _json
    corps = {"model": CLOUD_MODELE, "stream": True, "temperature": temperature, "max_tokens": max_tokens,
             "messages": [{"role": "system", "content": systeme}] + messages}
    with httpx.stream("POST", f"{CLOUD_URL}/chat/completions", json=corps,
                      headers={"Authorization": f"Bearer {_cle_cloud()}"},
                      timeout=httpx.Timeout(90, connect=10)) as reponse:
        reponse.raise_for_status()
        for ligne in reponse.iter_lines():
            if not ligne.startswith("data:"):
                continue
            donnees = ligne[5:].strip()
            if donnees == "[DONE]":
                break
            choix = (_json.loads(donnees).get("choices") or [{}])[0]
            morceau = (choix.get("delta") or {}).get("content")
            if morceau:
                yield morceau


def llm_disponible():
    return fournisseur() is not None


def prechauffer():
    """Charge le modèle local en mémoire en arrière-plan : le premier chargement prend
    jusqu'à deux minutes, les réponses suivantes quelques secondes."""
    if fournisseur() != "ollama":
        return

    def charger():
        try:
            httpx.post(f"{OLLAMA_URL}/api/chat", timeout=300, json={
                "model": OLLAMA_MODELE, "keep_alive": "30m", "stream": False,
                "messages": [{"role": "user", "content": "bonjour"}], "options": {"num_predict": 1}})
        except httpx.HTTPError:
            pass
    threading.Thread(target=charger, daemon=True).start()


def _formater_sources(sources):
    blocs = []
    for i, s in enumerate(sources, start=1):
        blocs.append(f'<source id="{i}" fichier="{s["metadata"]["source"]}">\n{s["texte"]}\n</source>')
    return "<sources>\n" + "\n".join(blocs) + "\n</sources>"


def _formater_web(pistes):
    """Résultats de la recherche en ligne (sites juridiques fiables), cités par leur lien."""
    if not pistes:
        return ""
    blocs = [f'<resultat lien="{p["url"]}" site="{p.get("site", "")}">\n{p.get("titre") or ""}\n'
             f'{(p.get("extrait") or "")[:900]}\n</resultat>' for p in pistes]
    return "<recherche_web>\n" + "\n".join(blocs) + "\n</recherche_web>\n\n"


CONSIGNES_OUVERTES = """

Cas particulier : la question sort des sources fournies (ou il n'y en a pas). Tu réponds QUAND MÊME à la \
question posée, concrètement, comme une avocate tunisienne expérimentée :
- utilise d'abord les <sources> et les <recherche_web> (cite les résultats web par leur lien en Markdown) ;
- complète avec tes connaissances générales du droit tunisien (Code des obligations et des contrats, Code \
pénal, Code du statut personnel, Code du travail, Code des droits réels, procédure), en le signalant par \
« en principe » ; n'invente JAMAIS un numéro d'article : cite un numéro seulement s'il figure dans les \
sources, sinon nomme le texte (« le Code des obligations et des contrats prévoit… ») ;
- dis qui a fait quoi et ce que la personne peut obtenir (remboursement, annulation, dommages-intérêts, \
plainte) ; donne les étapes concrètes (mise en demeure écrite, huissier notaire, plainte au procureur ou au \
poste de police, tribunal cantonal ou de première instance selon le montant), les preuves et les délais ;
- si la personne a elle-même commis une faute ou une infraction, réponds sans juger : ses droits, les \
risques, l'intérêt d'un avocat ; ne l'aide jamais à cacher des preuves ni à nuire à quelqu'un ;
- structure : ### Ce que je comprends ; ### Ce que dit la loi ; ### Ce que vous pouvez faire (liste \
numérotée) ; ### Les preuves à réunir ; ### Mon conseil ; puis une question pour préciser. 450 mots maximum."""


def _bloc_expertise(expertise):
    if not expertise:
        return ""
    from .conversation import resume_expertise
    return f"<analyse_experte>\n{resume_expertise(expertise)}\n</analyse_experte>\n\n"


def _requete_llm(question, sources, triage, historique, expertise=None, ouverte=False):
    messages = []
    for tour in (historique or [])[-8:]:  # contexte : les 4 derniers échanges
        if tour.get("role") in ("user", "assistant") and tour.get("content"):
            messages.append({"role": tour["role"], "content": tour["content"]})
    messages.append({"role": "user", "content": (
        f"{_formater_sources(sources)}\n\n{_bloc_expertise(expertise)}"
        f"Catégorie détectée par le module de triage : {triage['label']}.\n\n"
        f"Message de la personne :\n{question}"
    )})
    # L'API exige une alternance stricte user/assistant commençant par user.
    while messages and messages[0]["role"] != "user":
        messages.pop(0)
    return dict(
        model=MODELE_LLM,
        max_tokens=4000,
        system=CONSIGNES_SYSTEME + (CONSIGNES_OUVERTES if ouverte else ""),
        messages=messages,
        output_config={"effort": "low"},
        # Si le modèle principal décline, l'API relance la requête sur un modèle de repli.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )


# --- Modèle local (Ollama) ---------------------------------------------------------

def _messages_ollama(question, sources, triage, historique, langue, expertise=None):
    # Un petit modèle suit mieux des sources courtes : 4 passages, 700 caractères chacun.
    sources_courtes = [{**s, "texte": s["texte"][:700]} for s in sources[:4]]
    messages = [{"role": "system", "content": CONSIGNES_SYSTEME}]
    for tour in (historique or [])[-6:]:
        if tour.get("role") in ("user", "assistant") and tour.get("content"):
            messages.append({"role": tour["role"], "content": tour["content"][:1200]})
    messages.append({"role": "user", "content": (
        f"{_formater_sources(sources_courtes)}\n\n{_bloc_expertise(expertise)}"
        f"Catégorie détectée : {triage['label']}. Réponds en {LANGUES.get(langue, 'français')}, "
        f"en t'appuyant sur les sources ci-dessus et en les citant [n].\n\n"
        f"Message de la personne :\n{question}")})
    return messages


def generer_ollama_flux(question, sources, triage, historique=None, langue="fr", expertise=None):
    import json as _json

    corps = {"model": OLLAMA_MODELE, "stream": True, "keep_alive": "30m",
             "messages": _messages_ollama(question, sources, triage, historique, langue, expertise),
             "options": {"temperature": 0.3, "num_predict": 900 if expertise else 550, "num_ctx": 6144}}
    with httpx.stream("POST", f"{OLLAMA_URL}/api/chat", json=corps, timeout=httpx.Timeout(300, connect=5)) as reponse:
        reponse.raise_for_status()
        for ligne in reponse.iter_lines():
            if not ligne:
                continue
            donnees = _json.loads(ligne)
            morceau = donnees.get("message", {}).get("content", "")
            if morceau:
                yield morceau
            if donnees.get("done"):
                break


def generer_cloud_flux(question, sources, triage, historique=None, langue="fr", expertise=None, pistes=None,
                       ouverte=False):
    """Réponse complète par le modèle en ligne gratuit, à partir des sources et de la recherche web."""
    messages = []
    for tour in (historique or [])[-8:]:
        if tour.get("role") in ("user", "assistant") and tour.get("content"):
            messages.append({"role": tour["role"], "content": tour["content"][:2500]})
    sources_utiles = [{**s, "texte": s["texte"][:1500]} for s in sources[:6]]
    messages.append({"role": "user", "content": (
        f"{_formater_sources(sources_utiles)}\n\n{_formater_web(pistes)}{_bloc_expertise(expertise)}"
        f"Catégorie détectée : {triage['label']}. Le droit applicable est le droit TUNISIEN. "
        f"Réponds en {LANGUES.get(langue, 'français')}.\n\nMessage de la personne :\n{question}")})
    systeme = CONSIGNES_SYSTEME + (CONSIGNES_OUVERTES if ouverte else "")
    yield from _flux_cloud(systeme, messages, max_tokens=1800 if ouverte else 1400)


def generer_llm(question, sources, triage, historique=None, expertise=None):
    """Appelle Claude. Lève une exception en cas d'échec : l'appelant bascule en extractif."""
    import anthropic

    reponse = anthropic.Anthropic().beta.messages.create(**_requete_llm(question, sources, triage, historique, expertise))
    if reponse.stop_reason == "refusal":
        raise RuntimeError("réponse refusée par le modèle")
    texte = "".join(b.text for b in reponse.content if b.type == "text").strip()
    if not texte:
        raise RuntimeError("réponse vide")
    return texte


def generer_llm_flux(question, sources, triage, historique=None, expertise=None, ouverte=False):
    """Diffuse la réponse de Claude morceau par morceau."""
    import anthropic

    with anthropic.Anthropic().beta.messages.stream(**_requete_llm(question, sources, triage, historique, expertise, ouverte)) as flux:
        for morceau in flux.text_stream:
            yield morceau
        if flux.get_final_message().stop_reason == "refusal":
            raise RuntimeError("réponse refusée par le modèle")


CONSIGNES_ANALYSE = """Tu rédiges, pour la personne qui a décrit sa situation, une courte synthèse juridique \
à la manière de son avocate. Tu t'appuies UNIQUEMENT sur l'analyse structurée fournie (qualifications, \
articles, preuves, démarches, points de vigilance, limites des textes).

Rédige 120 à 180 mots, dans la langue de la situation décrite, en trois temps : ce que la loi permet de \
reprocher à l'autre partie et sur quel fondement ; la stratégie conseillée (preuves et ordre des démarches) ; \
les points faibles du dossier ou de la loi à anticiper. Ton calme et respectueux, sans jargon inutile, \
sans promettre d'issue judiciaire. Si l'analyse signale un danger immédiat, commence par le 197 ou le 193."""


def synthese_juridique(situation, analyse):
    """Synthèse rédigée par le modèle (Claude ou local) ; None sans modèle ou en cas d'échec."""
    choix = fournisseur()
    if not choix or not analyse["qualifications"]:
        return None
    try:
        import json as _json

        resume = {k: analyse[k] for k in ("urgence", "qualifications", "preuves", "demarches",
                                          "vigilance", "limites_loi")}
        contenu = (f"<situation>\n{situation}\n</situation>\n\n"
                   f"<analyse>\n{_json.dumps(resume, ensure_ascii=False)}\n</analyse>")
        if choix == "ollama":
            r = httpx.post(f"{OLLAMA_URL}/api/chat", timeout=300, json={
                "model": OLLAMA_MODELE, "stream": False, "keep_alive": "30m",
                "options": {"temperature": 0.3, "num_predict": 400, "num_ctx": 4096},
                "messages": [{"role": "system", "content": CONSIGNES_ANALYSE}, {"role": "user", "content": contenu}]})
            return r.json().get("message", {}).get("content", "").strip() or None
        if choix == "cloud":
            return "".join(_flux_cloud(CONSIGNES_ANALYSE, [{"role": "user", "content": contenu}], 700)).strip() or None

        import anthropic
        reponse = anthropic.Anthropic().beta.messages.create(
            model=MODELE_LLM,
            max_tokens=2000,
            system=CONSIGNES_ANALYSE,
            messages=[{"role": "user", "content": contenu}],
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if reponse.stop_reason == "refusal":
            return None
        return "".join(b.text for b in reponse.content if b.type == "text").strip() or None
    except Exception as erreur:
        print(f"[AMENA] synthèse juridique indisponible ({type(erreur).__name__}).")
        return None


def generer_extractif(question, sources, langue, triage=None, expertise=None):
    triage = triage or {"label": "information"}
    if expertise and expertise.get("qualifications"):
        # Situation reconnue : consultation structurée (compréhension, loi, étapes, preuves, conseil).
        from .conversation import composer_avocat
        return composer_avocat(expertise, sources, triage, langue)
    if sources and sources[0]["metadata"].get("type") == "monde":
        # Fiche pays de la Banque mondiale : déjà structurée, une ligne par thème.
        lignes = sources[0]["texte"].split("\n\n", 1)[-1].split("\n")
        corps = [lignes[0], "", "### Ce que dit la loi, thème par thème"] + [f"- {l} [1]" for l in lignes[1:]]
        complement = phrases_pertinentes(question, sources[1:], n=2) if len(sources) > 1 else []
        if complement:
            corps += ["", "### Textes complémentaires"]
            corps += [f"- {p} [{sources.index(c) + 1}]" for p, c in complement]
        return "\n".join(corps) + f"\n\n{CONCLUSION_EXTRACTIF[langue]}"
    return composer(question, sources, triage, langue)


def _question_extractive(question, triage):
    if triage["label"] == "urgence":
        # En urgence, on fait remonter les consignes de mise en sécurité plutôt que les
        # définitions juridiques, même si le message ne contient pas ces mots.
        return f"{question} danger immédiat appelez police garde nationale blessée sac de sécurité"
    return question


def generer(question, sources, triage, langue, historique=None, expertise=None, pistes=None):
    """Renvoie (texte, mode). Tente le LLM, retombe sur l'extractif en cas de problème."""
    morceaux, mode = [], "extractif"
    for genre, valeur in generer_flux(question, sources, triage, langue, historique, expertise, pistes):
        if genre == "texte":
            morceaux.append(valeur)
        else:
            mode = valeur
    return "".join(morceaux).strip(), mode


CONSIGNES_INTRO = """Tu es AMENA, une avocate tunisienne bienveillante qui reçoit une personne venue te consulter. \
Le droit applicable est TOUJOURS le droit tunisien (jamais le droit français ni un autre). \
À partir de son message et de l'analyse juridique fournie, écris UN SEUL paragraphe de 3 à 5 phrases : \
reformule avec tact ce que tu comprends de sa situation, explique que la loi la prend en compte, \
et rassure sur le fait qu'il existe des démarches concrètes. Ne suppose jamais le genre de la personne : \
écris au masculin générique ou avec des tournures neutres (« vous »), sans accord au féminin (pas de « licenciée », \
« frustrée », « enceinte ») sauf si son message l'indique. Pas de titre, pas de liste, pas d'article \
de loi, pas de numéro de téléphone (ils seront ajoutés ensuite). Réponds dans la langue de son message."""


def _intro_flux(choix, question, expertise, langue, historique):
    """Paragraphe personnalisé rédigé par le modèle (Claude ou local) pour la réponse hybride."""
    from .conversation import resume_expertise
    contenu = (f"<analyse_experte>\n{resume_expertise(expertise)}\n</analyse_experte>\n\n"
               f"Langue de réponse : {LANGUES.get(langue, 'français')}.\n\nMessage de la personne :\n{question}")
    if choix == "ollama":
        import json as _json
        corps = {"model": OLLAMA_MODELE, "stream": True, "keep_alive": "30m",
                 "messages": [{"role": "system", "content": CONSIGNES_INTRO}, {"role": "user", "content": contenu}],
                 "options": {"temperature": 0.4, "num_predict": 220, "num_ctx": 4096}}
        with httpx.stream("POST", f"{OLLAMA_URL}/api/chat", json=corps, timeout=httpx.Timeout(300, connect=5)) as r:
            r.raise_for_status()
            for ligne in r.iter_lines():
                if ligne:
                    donnees = _json.loads(ligne)
                    if donnees.get("message", {}).get("content"):
                        yield donnees["message"]["content"]
                    if donnees.get("done"):
                        break
        return
    if choix == "cloud":
        yield from _flux_cloud(CONSIGNES_INTRO, [{"role": "user", "content": contenu}], 400, 0.4)
        return
    import anthropic
    with anthropic.Anthropic().beta.messages.stream(
            model=MODELE_LLM, max_tokens=800, system=CONSIGNES_INTRO,
            messages=[{"role": "user", "content": contenu}], output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default") as flux:
        yield from flux.text_stream


def _flux_hybride(choix, question, sources, triage, langue, historique, expertise):
    """Réponse hybride : paragraphe personnalisé du modèle + parties juridiques de la base d'expertise.
    Le modèle ne peut ainsi ni inventer un article de loi ni oublier une étape."""
    from .conversation import ACCUEIL, TITRES_AVOCAT, composer_avocat, comprehension_avocat
    lg = langue if langue in ("fr", "ar", "dz") else "fr"
    if triage["label"] == "urgence":
        yield ACCUEIL["urgence"][lg] + "\n\n"
    yield f"### {TITRES_AVOCAT['comprends'][lg]}\n"
    ecrit = False
    # Le petit modèle local répond en français même à une question en arabe ou en derja : dans ces
    # langues, sans Claude, le paragraphe vient de la base d'expertise, déjà rédigée dans la bonne langue.
    if choix == "ollama" and lg in ("ar", "dz"):
        yield comprehension_avocat(expertise, lg) + "\n\n"
        for morceau in re.findall(r"\S+\s*", composer_avocat(expertise, sources, triage, langue, sans_intro=True)):
            yield morceau
        return
    try:
        for morceau in _intro_flux(choix, question, expertise, langue, historique):
            ecrit = True
            yield morceau
    except Exception as erreur:
        print(f"[AMENA] paragraphe personnalisé indisponible ({type(erreur).__name__}).")
    if not ecrit:
        yield comprehension_avocat(expertise, lg)
    yield "\n\n"
    for morceau in re.findall(r"\S+\s*", composer_avocat(expertise, sources, triage, langue, sans_intro=True)):
        yield morceau


def _deja_traitee(expertise, historique):
    """Vrai si une réponse précédente d'AMENA a déjà présenté cette situation (même libellé)."""
    if not expertise or not expertise.get("qualifications") or not historique:
        return False
    # Marqueurs de la fiche déjà donnée : le libellé (version sans modèle) ou ses questions de suivi.
    marqueurs = [expertise["qualifications"][0]["libelle"].lower()] + [q.lower() for q in expertise.get("questions", [])]
    return any(t.get("role") == "assistant" and any(m in (t.get("content") or "").lower() for m in marqueurs)
               for t in historique)


MODES = {"claude": "llm", "cloud": "llm", "ollama": "llm-local"}


def _flux_modele(choix, question, sources, triage, historique, langue, expertise, pistes=None, ouverte=False):
    if choix == "claude":
        if pistes or ouverte:
            # Même consignes « question ouverte » et mêmes résultats web que pour le modèle en ligne.
            question = f"{_formater_web(pistes)}{question}"
        return generer_llm_flux(question, sources, triage, historique, expertise, ouverte)
    if choix == "cloud":
        return generer_cloud_flux(question, sources, triage, historique, langue, expertise, pistes, ouverte)
    return generer_ollama_flux(question, sources, triage, historique, langue, expertise)


def generer_flux(question, sources, triage, langue, historique=None, expertise=None, pistes=None):
    """Générateur : ("texte", morceau)... puis ("mode", "llm" | "llm-local" | "extractif")."""
    choix = fournisseur()
    deja = _deja_traitee(expertise, historique)
    generale = bool(expertise and expertise.get("generale"))
    if deja and expertise.get("qualifications") and not generale:
        # Suite de la consultation : la fiche complète a déjà été donnée. On répond aux précisions
        # avec l'historique (modèle) ou, sans modèle adapté à la langue, par le conseil et les questions.
        lg = langue if langue in ("fr", "ar", "dz") else "fr"
        if choix and not (choix == "ollama" and lg in ("ar", "dz")):
            try:
                envoye = False
                for morceau in _flux_modele(choix, question, sources, triage, historique, langue, expertise, pistes):
                    envoye = True
                    yield "texte", morceau
                if envoye:
                    yield "mode", MODES[choix]
                    return
            except Exception as erreur:
                print(f"[AMENA] modèle indisponible pour la suite ({type(erreur).__name__}).")
        from .conversation import suite_avocat
        for morceau in re.findall(r"\S+\s*", suite_avocat(expertise, historique, lg)):
            yield "texte", morceau
        yield "mode", "extractif"
        return
    if choix and expertise and expertise.get("qualifications") and not (generale and choix in ("claude", "cloud")):
        for morceau in _flux_hybride(choix, question, sources, triage, langue, historique, expertise):
            yield "texte", morceau
        yield "mode", MODES[choix]
        return
    # Question hors des situations connues : un grand modèle (Claude ou en ligne) répond à la question
    # elle-même, avec les lois trouvées, la recherche web et ses connaissances du droit tunisien.
    ouverte = choix in ("claude", "cloud") and (generale or not sources or bool(pistes))
    if choix and (sources or ouverte):
        envoye = False
        try:
            flux = _flux_modele(choix, question, sources, triage, historique, langue, expertise, pistes, ouverte)
            for morceau in flux:
                envoye = True
                yield "texte", morceau
            if envoye:
                yield "mode", MODES[choix]
                return
        except Exception as erreur:  # réseau, quota, refus : on ne laisse jamais sans réponse
            print(f"[AMENA] modèle indisponible ({type(erreur).__name__}: {erreur}), mode extractif.")
            if envoye:
                yield "texte", "\n\n"
    texte = generer_extractif(_question_extractive(question, triage), sources, langue, triage, expertise)
    # Découpage par mots : l'interface les affiche progressivement, comme une frappe en direct.
    for morceau in re.findall(r"\S+\s*", texte):
        yield "texte", morceau
    yield "mode", "extractif"
