"""Conversation « professionnelle » : contexte, réponse structurée, citations, suggestions.

    contextualiser()   une relance courte (« et au Maroc ? », « comment je fais ? ») est
                       complétée par le sujet du message précédent avant la recherche ;
    composer()         réponse extractive structurée comme une vraie conversation :
                       accueil adapté, « Ce que disent les textes » avec citations [n],
                       « Ce que vous pouvez faire », question de relance ;
    suggestions()      trois questions de suivi pertinentes, plus des actions (analyse, aide).
"""

import re

from .recherche import phrases_pertinentes
from .securite import normaliser

_RELANCE = re.compile(r"^(et|mais|aussi|alors|donc|w|و)\b|\b(ça|cela|ceci|celle-ci|celui-ci|là|dans ce cas|"
                      r"comment je fais|quoi faire|et si|et pour|hedha|hadhi|هذا|ذلك)\b", re.IGNORECASE)

ACCUEIL = {
    "urgence": {
        "fr": "**Votre sécurité passe avant tout.** Si vous êtes en danger maintenant, appelez le **197** (police) "
              "ou le **193** (garde nationale). En cas de blessure ou de pensées suicidaires, le **190** (SAMU).",
        "ar": "**سلامتك قبل كل شيء.** إذا كنت في خطر الآن اتصل بالرقم **197** أو **193**، وفي حالة إصابة بالرقم **190**.",
        "dz": "**Slemtek 9bal kol chay.** Ken inti fi khatar tawa, kallem **197** walla **193**. Ken mjarra7, kallem **190**.",
    },
    "juridique": {
        "fr": "Bonne question. Voici ce que prévoit la loi sur ce point, et comment l'utiliser concrètement.",
        "ar": "سؤال مهم. إليك ما ينص عليه القانون وكيف يمكنك الاستفادة منه.",
        "dz": "Sou2el behi. Hédha chnowa y9oul el 9anoun, w kifech testa3mlou.",
    },
    "soutien": {
        "fr": "Merci de m'avoir écrit. Ce que vous vivez compte, et vous n'avez pas à l'affronter seul(e). "
              "Voici quelques repères qui peuvent vous aider.",
        "ar": "شكرا لأنك كتبت لي. ما تعيشه مهم، ولست مضطرا لمواجهته وحدك. إليك بعض المعالم.",
        "dz": "Ya3tik essa7a 3la elli kteblna. Elli 9a3da t3ichou yhemm, w mouch lazem twajhou wa7dek.",
    },
    "information": {
        "fr": "Voici les informations utiles pour vous orienter.",
        "ar": "إليك المعلومات المفيدة لتوجيهك.",
        "dz": "Hédhom el ma3loumet elli tnajjem test7a99hom.",
    },
}
TITRES = {
    "textes": {"fr": "Ce que disent les textes", "ar": "ماذا تقول النصوص", "dz": "Chnowa t9oul el nousous"},
    "actions": {"fr": "Ce que vous pouvez faire", "ar": "ما يمكنك فعله", "dz": "Chnowa tnajjem ta3mel"},
}
RELANCE = {
    "urgence": {"fr": "Êtes-vous en sécurité en ce moment ? Je peux vous indiquer comment préparer un départ ou vers qui vous tourner.",
                "ar": "هل أنت في أمان الآن؟ يمكنني أن أدلك على كيفية الاستعداد للمغادرة.",
                "dz": "Inti fi amen tawa ? Nnajjem n9ollek kifech t7adher rou7ek."},
    "juridique": {"fr": "Souhaitez-vous que j'analyse votre situation précise, avec les preuves à réunir et les points faibles à anticiper ?",
                  "ar": "هل تريد أن أحلل وضعيتك بدقة مع الأدلة ونقاط الضعف؟",
                  "dz": "T7eb n7allel wadh3itek bel détail ?"},
    "soutien": {"fr": "Voulez-vous m'en dire un peu plus sur ce qui se passe ? Je reste là pour vous écouter et vous orienter.",
                "ar": "هل تريد أن تحكي لي أكثر؟ أنا هنا للاستماع والتوجيه.",
                "dz": "T7eb t7kili akther ? Ena houni nesma3ek."},
    "information": {"fr": "Avez-vous besoin d'autre chose, par exemple les démarches pour porter plainte ?",
                    "ar": "هل تحتاج شيئا آخر، مثلا إجراءات تقديم الشكاية؟",
                    "dz": "T7eb 7aja okhra, kima kifech t9ayed chekaya ?"},
}
AUCUNE = {
    "fr": "Je n'ai pas trouvé d'information assez précise dans mes sources pour vous répondre avec certitude. "
          "Un(e) avocat(e) ou une maison du droit pourra vous orienter ; en cas de violence, le **1899** (gratuit) répond 24 h/24.",
    "ar": "لم أجد معلومة دقيقة بما يكفي في مصادري. يمكن لمحام أو لدار الحقوق أن يوجهك، وفي حالة العنف الرقم الأخضر **1899**.",
    "dz": "Ma l9itech ma3loumet dhe9i9a. Kallem el **1899** bilech, ynajmou y3awnouk.",
}

_ACTION = re.compile(r"\b(appelez|appeler|déposez|déposer|demandez|demander|rendez-vous|conservez|conserver|faites|"
                     r"gardez|préparez|notez|signalez|contactez|consultez|vous pouvez|il est recommandé|saisir|"
                     r"kallem|emchi|اتصلي|قدمي|يمكنك|احتفظي)\b", re.IGNORECASE)

# Questions de suivi selon les fiches et textes consultés (premier élément pertinent).
SUIVIS = {
    "fiche:01_loi_58_2017": ["Qu'est-ce qu'une ordonnance de protection ?", "Quelles formes de violence la loi reconnaît-elle ?"],
    "fiche:02_porter_plainte": ["Comment obtenir un certificat médical ?", "Quelles preuves rassembler ?"],
    "fiche:03_numeros_urgence": ["Que dire au téléphone en cas d'urgence ?", "Quelles associations peuvent m'aider ?"],
    "fiche:04_soutien_psychologique": ["Comment savoir si ma relation est violente ?", "Comment aider une amie ?"],
    "fiche:05_faq_arabe_darija": ["كيف أقدم شكاية", "هل يمكنني طلب قرار حماية"],
    "fiche:06_violence_economique_travail": ["Que faire si la pension n'est pas payée ?", "Le harcèlement au travail est-il puni ?"],
    "loi:tn-code-penal": ["Que dit l'article 226 ter sur le harcèlement ?", "Comment le viol est-il défini depuis 2017 ?"],
    "loi:tn-csp": ["Comment demander le divorce pour préjudice ?", "Qui obtient la garde des enfants ?"],
    "loi:tn-loi-2017-58": ["Qu'est-ce qu'une ordonnance de protection ?", "Puis-je retirer ma plainte ?"],
}
SUIVIS_DEFAUT = {
    "urgence": ["Que mettre dans un sac de sécurité ?", "Où trouver un hébergement d'urgence ?"],
    "juridique": ["Comment porter plainte ?", "Ai-je droit à un avocat gratuit ?"],
    "soutien": ["Comment savoir si ma relation est violente ?", "Je voudrais parler à quelqu'un"],
    "information": ["Quel est le numéro vert ?", "Quelles associations peuvent m'aider ?"],
}


def contextualiser(message, historique):
    """Complète une relance courte avec le dernier message de l'utilisatrice."""
    precedents = [t["content"] for t in historique or [] if t.get("role") == "user" and t.get("content")]
    if not precedents:
        return message
    court = len(normaliser(message).split()) <= 6
    if court or _RELANCE.search(message.strip()):
        return f"{precedents[-1]} {message}"
    return message


def _citer(phrase, sources):
    for i, s in enumerate(sources, start=1):
        if phrase in s["texte"]:
            return f"{phrase} [{i}]"
    return phrase


# --- Petite conversation : on ne lance pas une recherche juridique pour « bonjour » ---------

_PETITE = [
    ("salut", re.compile(r"^(bonjour|bonsoir|salut|coucou|hello|hi|hey|aslema|3aslema|asslema|salem|ahla|marhba|"
                         r"مرحبا|السلام عليكم|اهلا|صباح الخير|مساء الخير)\b")),
    ("merci", re.compile(r"\b(merci|thanks|thank you|ya3tik essa7a|ya3tik saha|barcha merci|شكرا|بارك الله)\b")),
    ("revoir", re.compile(r"\b(au revoir|bye|a bientot|bslema|beslema|مع السلامة|الى اللقاء)\b")),
    ("identite", re.compile(r"(qui es[- ]tu|tu es qui|t'es qui|c'?est quoi amena|que fais[- ]tu|tu sers a quoi|"
                            r"chkoun inti|chnowa amena|من انت|ماذا تفعلين)")),
    ("cava", re.compile(r"^(ca va|cv|comment vas[- ]tu|comment allez[- ]vous|labes|chniya a7walek|كيف حالك|لاباس)\b")),
]
REPONSES_PETITES = {
    "salut": {
        "fr": "Bonjour, je suis **AMENA**, votre assistante juridique. Je peux vous expliquer vos droits "
              "(travail, contrats, famille, pénal, numérique, violences), les démarches à suivre, ou analyser votre situation en détail.\n\n"
              "Que se passe-t-il pour vous aujourd'hui ?",
        "ar": "مرحبا، أنا **أمانة**، مساعدتك القانونية. يمكنني أن أشرح لك حقوقك (الشغل، العقود، الأسرة، الجزائي، الرقمي، العنف) والإجراءات اللازمة.\n\nماذا يحدث معك اليوم؟",
        "dz": "Aslema, ena **AMENA**. Nnajjem n9ollek 7ou9ou9ek, kifech t9ayed chekaya, walla n7allel wadh3itek.\n\nChnowa sar m3ak ?",
    },
    "merci": {
        "fr": "Avec plaisir. Je reste là si vous avez d'autres questions. Et n'oubliez pas : le **1899** est gratuit "
              "si vous souhaitez parler à quelqu'un.",
        "ar": "بكل سرور. أنا هنا إن كانت لديك أسئلة أخرى. الرقم **1899** مجاني إن أردت التحدث مع شخص.",
        "dz": "Bil fara7. Ena houni ken 3andek asila okhra. El **1899** bilech ken t7eb tkallem 7ad.",
    },
    "revoir": {
        "fr": "Prenez soin de vous. Pour effacer toute trace de cette visite, utilisez le bouton **Sortie rapide**.",
        "ar": "اعتن بنفسك. لمسح أثر هذه الزيارة استعمل زر **خروج سريع**.",
        "dz": "Rodd belek 3la rou7ek. Bech tfasakh kol chay, ésta3mel **Sortie rapide**.",
    },
    "identite": {
        "fr": "Je suis **AMENA**, une assistante juridique (avocate numérique) pour toute personne en Tunisie.\n\n"
              "### Ce que je peux faire\n- Expliquer la loi : Constitution, Code du travail, Code des obligations et contrats, Code pénal, procédure pénale, loi 2017-58…\n"
              "- Vous guider dans vos démarches : réclamation, plainte, recours, aide juridictionnelle\n"
              "- Analyser votre situation comme une avocate : preuves, démarches, points faibles\n"
              "- Comparer les lois de 190 pays (données de la Banque mondiale)\n\n"
              "Je ne remplace pas un(e) avocat(e), mais je peux vous aider à préparer vos démarches. Par quoi voulez-vous commencer ?",
        "ar": "أنا **أمانة**، مساعدة قانونية لكل شخص في تونس. أشرح القانون، أرشدك في إجراءاتك، وأحلل وضعيتك.\n\nبماذا تريد أن نبدأ؟",
        "dz": "Ena **AMENA**, n3awen ay wa7ed fi Tounes : nfasser el 9anoun, nwarrik el ijra2at, w n7allel wadh3itek.",
    },
    "cava": {
        "fr": "Merci de demander. Et vous, comment allez-vous ? Si quelque chose vous inquiète, vous pouvez m'en parler librement.",
        "ar": "شكرا على سؤالك. وأنت، كيف حالك؟ إن كان هناك ما يقلقك يمكنك التحدث معي بحرية.",
        "dz": "Ya3tik essa7a. W inti labes ? Ken famma 7aja t9alle9ek, a7kili.",
    },
}


def petite_discussion(texte, langue):
    """Réponse directe aux salutations, remerciements, « qui es-tu »… sinon None."""
    t = normaliser(texte).strip(" ?!.")
    if len(t.split()) > 8:
        return None
    for genre, motif in _PETITE:
        if motif.search(t):
            return REPONSES_PETITES[genre].get(langue, REPONSES_PETITES[genre]["fr"])
    return None


# --- Réponses extractives cohérentes -------------------------------------------------------

_PROCEDURE = re.compile(r"\b(comment|demarche|etape|procedure|que faire|quoi faire|marche a suivre|kifech|"
                        r"chnowa na3mel|كيف|ماذا افعل)\b")


def _etapes_procedure(sources):
    """Si une source appartient à une fiche organisée en « Étape n », renvoie ces étapes dans l'ordre."""
    from .config import DOSSIER_KB
    from .ingestion import sections_markdown

    for i, s in enumerate(sources, start=1):
        fichier = s["metadata"].get("source", "")
        if not fichier.endswith(".md"):
            continue
        sections = sections_markdown(DOSSIER_KB / fichier)
        etapes = [x for x in sections if x["chemin"][-1].lower().startswith("étape")]
        if len(etapes) >= 3:
            return i, sections[0]["chemin"][0], etapes
    return None


def _premieres_phrases(texte, n=1):
    phrases = re.split(r"(?<=[.!?؟])\s+(?=[A-ZÀ-ÖØ-Þ؀-ۿ«])", texte)
    return " ".join(phrases[:n])


def composer(question, sources, triage, langue):
    """Réponse extractive structurée, en Markdown léger (gras, titres ###, listes, citations [n])."""
    label = triage["label"]
    if not sources:
        return f"{ACCUEIL[label][langue]}\n\n{AUCUNE[langue]}"

    blocs = [ACCUEIL[label][langue]]
    deja = set()

    # 1. Question de procédure : on présente toutes les étapes, dans l'ordre.
    procedure = _etapes_procedure(sources) if _PROCEDURE.search(normaliser(question)) and label != "urgence" else None
    if procedure:
        n, titre_fiche, etapes = procedure
        lignes = [f"{i}. **{e['chemin'][-1].split(':', 1)[-1].strip().capitalize()}** — {_premieres_phrases(e['texte'])} [{n}]"
                  for i, e in enumerate(etapes, start=1)]
        blocs.append(f"### {titre_fiche.split(':')[0].strip()}\n" + "\n".join(lignes))
        deja.update(e["texte"] for e in etapes)
    else:
        # 2. Sinon : les deux passages les plus pertinents, chacun présenté comme un tout cohérent,
        #    sous le titre de sa section, avec ses phrases les plus utiles dans l'ordre du texte.
        retenus, sections_vues = [], set()
        for s in sources:
            section = s["metadata"]["chemin"][-1]
            if section in sections_vues:
                continue
            sections_vues.add(section)
            retenus.append(s)
            if len(retenus) == 2:
                break
        for s in retenus:
            n = sources.index(s) + 1
            phrases = [p for p, _ in phrases_pertinentes(question, [s], n=3)]
            if langue == "ar":
                phrases = [p for p in phrases if re.search(r"[؀-ۿ]", p)] or phrases
            if not phrases:
                continue
            deja.update(phrases)
            titre = s["metadata"]["chemin"][-1]
            blocs.append(f"### {titre}\n" + " ".join(phrases) + f" [{n}]")

    # 3. Ce que vous pouvez faire : phrases d'action non encore citées.
    actions = [p for p, _ in phrases_pertinentes(question, sources, n=10)
               if _ACTION.search(p) and not any(p in d for d in deja)][:3]
    if actions:
        blocs.append(f"### {TITRES['actions'][langue]}\n" + "\n".join(f"- {_citer(p, sources)}" for p in actions))
    blocs.append(RELANCE[label][langue])
    return "\n\n".join(blocs)


# --- Consultation « avocate » : quand le message décrit une situation reconnue ----------------

TITRES_AVOCAT = {
    "comprends": {"fr": "Ce que je comprends de votre situation", "ar": "ما فهمته من وضعيتك", "dz": "Chnowa fhemt men wadh3itek"},
    "loi": {"fr": "Ce que dit la loi", "ar": "ماذا يقول القانون", "dz": "Chnowa y9oul el 9anoun"},
    "etapes": {"fr": "Les étapes à suivre, dans l'ordre", "ar": "الخطوات بالترتيب", "dz": "El khatwet bel tartib"},
    "preuves": {"fr": "Les preuves à réunir", "ar": "الأدلة التي يجب جمعها", "dz": "El adilla elli lazem tjam3ha"},
    "savoir": {"fr": "Ce qu'il faut savoir", "ar": "ما يجب معرفته", "dz": "Chnowa lazem ta3ref"},
    "conseil": {"fr": "Mon conseil", "ar": "نصيحتي", "dz": "Nasi7ti"},
    "questions": {"fr": "Pour aller plus loin, dites-moi", "ar": "لنتعمق أكثر، أخبرني", "dz": "Bech nemchiw ab3ed, 9olli"},
}
MOTS = {
    "art": {"fr": "art.", "ar": "الفصل", "dz": "el fasl"},
    "delai": {"fr": "Délai", "ar": "الأجل", "dz": "El ajal"},
    "faible": {"fr": "Point faible à anticiper", "ar": "نقطة ضعف يجب توقعها", "dz": "No9tet dh3f"},
    "releve": {"fr": "Vous décrivez une situation qui relève de : {}.", "ar": "تتعلق وضعيتك بـ: {}.",
               "dz": "El wadh3iya mte3ek tetsamma : {}."},
}
# Nom des textes dans la langue de la réponse (les titres de la base sont en français).
NOMS_TEXTES = {
    "tn-off-code-penal": {"ar": "المجلة الجزائية", "dz": "El majalla el jaza2iya"},
    "tn-off-coc": {"ar": "مجلة الالتزامات والعقود", "dz": "Majallet el iltizamat w el 3o9oud"},
    "tn-off-code-procedure-penale": {"ar": "مجلة الإجراءات الجزائية", "dz": "Majallet el ijra2at el jaza2iya"},
    "tn-off-code-travail": {"ar": "مجلة الشغل", "dz": "Majallet el chghol"},
    "tn-off-constitution-2022": {"ar": "الدستور", "dz": "El destour"},
    "tn-off-loi-2017-58": {"ar": "القانون الأساسي عدد 58 لسنة 2017", "dz": "9anoun 58 lsnet 2017"},
    "tn-off-code-droits-reels": {"fr": "Code des droits réels", "ar": "مجلة الحقوق العينية", "dz": "Majallet el 7o9ou9 el 3ayniya"},
}
URGENCE_CONSEIL = {
    "fr": "Mettez-vous d'abord en sécurité : appelez le **197** ou le **193**. Le reste peut attendre que vous soyez à l'abri.",
    "ar": "ضع نفسك أولا في مأمن: اتصل بالرقم **197** أو **193**. الباقي يمكن أن ينتظر حتى تكون في أمان.",
    "dz": "Rod belek 3la rou7ek lowel : kallem **197** walla **193**. El ba9i yestanna 7atta tkoun fi amen.",
}
RELANCE_AVOCAT = {
    "fr": "Souhaitez-vous que je prépare **le dossier à remettre à votre avocat(e)** (faits, chronologie, articles, preuves, "
          "questions à poser) ? Vous pourrez le télécharger en PDF.",
    "ar": "هل تريد أن أعد **ملفا لمحاميك** (الوقائع، التسلسل الزمني، الفصول، الأدلة، الأسئلة)؟ يمكنك تحميله بصيغة PDF.",
    "dz": "T7eb n7adherlek **dossier lel avocat** mte3ek (el wa9a2e3, el fsoul, el adilla) ? Tnajjem ta3mlou PDF.",
}


def composer_avocat(expertise, sources, triage, langue, sans_intro=False):
    """Réponse structurée comme une consultation : compréhension, loi, étapes, preuves, à savoir, conseil.

    sans_intro=True : l'accueil et « Ce que je comprends » sont rédigés par le modèle de langage
    (réponse hybride) ; seules les parties juridiques, vérifiables, sont produites ici."""
    label = triage["label"]
    q = expertise["qualifications"]
    lg = langue if langue in ("fr", "ar", "dz") else "fr"

    def citation(texte_id, article):
        for i, s in enumerate(sources, start=1):
            chemin = s["metadata"].get("chemin", [])
            if s["metadata"].get("element") == f"loi:{texte_id}" and chemin and chemin[-1].startswith(f"Art. {article}"):
                return f" [{i}]"
        return ""

    blocs = []
    if not sans_intro:
        blocs.append(ACCUEIL[label][lg])
        blocs.append(f"### {TITRES_AVOCAT['comprends'][lg]}\n" + comprehension_avocat(expertise, lg))

    lignes_loi, vus = [], set()
    for x in q:
        for f in x["fondements"]:
            cle = (f["texte_id"], f["article"])
            if cle in vus:
                continue
            vus.add(cle)
            # « art. 218 » pour un vrai numéro, sinon le titre de la disposition (« Ordonnance de protection »).
            article = f"{MOTS['art'][lg]} {f['article']}" if re.match(r"^\d", f["article"]) else f"« {f['titre']} »"
            # Explication simple dans la langue de la question ; en français, l'article exact suit en citation.
            texte_loi = f.get("explication") or f["contenu"]
            if f.get("explication") and lg == "fr":
                texte_loi += f"\n  > « {f['contenu'][:420]}{'…' if len(f['contenu']) > 420 else ''} »"
            nom = NOMS_TEXTES.get(f["texte_id"], {}).get(lg) or f["texte"].split("(")[0].strip()
            lignes_loi.append(f"- **{nom} — {article}** : {texte_loi}"
                              f"{citation(f['texte_id'], f['article'])}")
    lignes_loi += [f"- {p}" for p in expertise.get("principes", [])]
    if lignes_loi:
        blocs.append(f"### {TITRES_AVOCAT['loi'][lg]}\n" + "\n".join(lignes_loi[:6]))

    if expertise["demarches"]:
        blocs.append(f"### {TITRES_AVOCAT['etapes'][lg]}\n" +
                     "\n".join(f"{i}. {d}" for i, d in enumerate(expertise["demarches"][:7], start=1)))
    if expertise["preuves"]:
        blocs.append(f"### {TITRES_AVOCAT['preuves'][lg]}\n" + "\n".join(f"- {p}" for p in expertise["preuves"][:6]))

    savoir = [f"- **{MOTS['delai'][lg]}** : {d}" for d in expertise["delais"][:2]]
    savoir += [f"- **{MOTS['faible'][lg]}** : {v}" for v in expertise["vigilance"][:3]]
    if lg == "fr":  # les limites relevées par les associations ne sont rédigées qu'en français
        savoir += [f"- **Limite de la loi** : {l['contenu']}" for l in expertise["limites_loi"] if l["type"] == "lacune"][:2]
    if savoir:
        blocs.append(f"### {TITRES_AVOCAT['savoir'][lg]}\n" + "\n".join(savoir))

    if expertise["urgence"]:
        conseil = URGENCE_CONSEIL[lg]
    elif expertise.get("conseil"):
        conseil = expertise["conseil"]
    else:
        premiere = next((d for d in expertise["demarches"] if not d.lower().startswith("danger")), expertise["demarches"][0])
        # Le 1899 (violences faites aux femmes) n'est proposé que si la situation relève des violences.
        violence = re.search(r"violen|harc[eè]lement|agression|coups", str(expertise["qualifications"]), re.IGNORECASE)
        conseil = (f"Commencez par ceci : **{premiere[0].lower() + premiere[1:]}**. Gardez une copie de chaque document "
                   f"en lieu sûr, et faites-vous accompagner : l'aide judiciaire permet d'avoir un avocat gratuitement "
                   f"si vos revenus sont insuffisants"
                   + (", et le **1899** peut vous orienter." if violence else "."))
    blocs.append(f"### {TITRES_AVOCAT['conseil'][lg]}\n{conseil}")
    # La consultation continue : les questions qui permettent d'aller plus loin.
    if expertise.get("questions"):
        blocs.append(f"### {TITRES_AVOCAT['questions'][lg]}\n" + "\n".join(f"- {x}" for x in expertise["questions"]))
    # Avec des questions de suivi, le dossier PDF est proposé après les précisions (réponse suivante).
    if not expertise.get("generale") and not expertise.get("questions"):
        blocs.append(RELANCE_AVOCAT[lg])
    return "\n\n".join(blocs)


SUITE = {
    "merci": {"fr": "Merci pour ces précisions, elles m'aident à mieux cerner votre situation.",
              "ar": "شكرا على هذه التوضيحات، فهي تساعدني على فهم وضعيتك بشكل أفضل.",
              "dz": "Ya3tik essa7a 3al tawdhi7at, t3awenni nefhem wadh3itek akther."},
    "etape": {"fr": "Votre prochaine étape", "ar": "خطوتك القادمة", "dz": "El khatwa el jeya"},
    "rappel": {"fr": "Les articles, les étapes et les preuves de ma réponse précédente restent valables.",
               "ar": "الفصول والخطوات والأدلة الواردة في إجابتي السابقة تبقى صالحة.",
               "dz": "El fsoul w el khatwet w el adilla elli 9oltlek 3lihom 9bal mezelou sal7in."},
}


def suite_avocat(expertise, historique, lg="fr"):
    """Suite de consultation sans modèle : on ne répète pas toute la fiche, on avance."""
    blocs = [SUITE["merci"][lg]]
    premiere = next((d for d in expertise["demarches"] if not d.lower().startswith("danger")), None)
    if premiere:
        blocs.append(f"### {SUITE['etape'][lg]}\n**{premiere}**")
    if expertise.get("conseil"):
        blocs.append(f"### {TITRES_AVOCAT['conseil'][lg]}\n{expertise['conseil']}")
    blocs.append(SUITE["rappel"][lg])
    blocs.append(RELANCE_AVOCAT[lg])
    return "\n\n".join(blocs)


def comprehension_avocat(expertise, lg="fr"):
    q = expertise["qualifications"]
    libelles = ", ".join(f"**{x['libelle'].lower()}**" for x in q)
    lignes = [MOTS["releve"][lg].format(libelles)] if not expertise.get("generale") else []
    lignes += [f"- {x['qualification']}" for x in q[:3]]
    return "\n".join(lignes)

def resume_expertise(expertise):
    """Version compacte de l'analyse, transmise au modèle de langage comme base de raisonnement."""
    lignes = []
    for x in expertise["qualifications"]:
        lignes.append(f"Situation : {x['libelle']} — {x['qualification']}")
        for f in x["fondements"]:
            lignes.append(f"  Fondement : {f['texte']}, art. {f['article']} : {f['contenu']}")
    lignes += [f"Étape : {d}" for d in expertise["demarches"][:7]]
    lignes += [f"Preuve : {p}" for p in expertise["preuves"][:6]]
    lignes += [f"Délai : {d}" for d in expertise["delais"][:2]]
    lignes += [f"Point faible : {v}" for v in expertise["vigilance"][:3]]
    lignes += [f"Limite de la loi : {l['contenu']}" for l in expertise["limites_loi"][:2]]
    lignes += [f"Principe : {p}" for p in expertise.get("principes", [])]
    if expertise.get("conseil"):
        lignes.append(f"Conseil prioritaire : {expertise['conseil']}")
    return "\n".join(lignes)


def suggestions(triage, sources, langue):
    """Trois questions de suivi, sans répéter la même deux fois."""
    vues, sortie = set(), []
    for s in sources:
        for q in SUIVIS.get(s["metadata"].get("element") or "", []):
            if q not in vues:
                vues.add(q)
                sortie.append(q)
    for q in SUIVIS_DEFAUT[triage["label"]]:
        if q not in vues:
            vues.add(q)
            sortie.append(q)
    if langue == "ar":
        sortie = [q for q in sortie if re.search(r"[؀-ۿ]", q)] or ["كيف أقدم شكاية", "ما هي أرقام النجدة المجانية"]
    return sortie[:3]
