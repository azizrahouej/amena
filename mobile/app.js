// AMENA mobile : application à onglets (accueil, chat, analyse, lois, aide, dossier).
// Même serveur et même base juridique que le site. Rien n'est stocké : ni localStorage, ni
// cookie ; la conversation vit en mémoire et disparaît à la fermeture.

const API = "/api";
const PHOTOS = "/static/img/photos";

// --- Textes (français / arabe) ------------------------------------------------------------------
const T = {
  fr: {
    "nav.accueil": "Accueil", "nav.chat": "Parler", "nav.analyse": "Analyse", "nav.lois": "Lois", "nav.aide": "Aide",
    "ac.titre": "Votre avocate de poche", "ac.texte": "Posez votre question de droit avec vos mots, en français, en arabe ou en derja. AMENA vous explique la loi tunisienne et les démarches. Gratuit et confidentiel.",
    "ac.parler": "Parler à AMENA", "ac.domaines": "Choisissez un sujet", "ac.urgence": "En danger ? Appelez le 197 (police) ou le 190 (SAMU).", "ac.appeler": "Appeler",
    "chat.vide.t": "Que se passe-t-il ?", "chat.vide.d": "Décrivez votre situation : AMENA cite les articles de loi, les étapes, les preuves à réunir, puis vous pose des questions pour aller plus loin.",
    "chat.placeholder": "Écrivez votre message…", "chat.envoyer": "Envoyer", "chat.reflexion": "AMENA réfléchit…", "chat.sources": "Sources citées",
    "chat.erreur": "Le serveur ne répond pas. Vérifiez votre connexion, puis réessayez.", "chat.nouveau": "Nouvelle discussion",
    "pdf.q": "Voulez-vous que je prépare le PDF de votre dossier pour votre avocat(e) ?", "pdf.oui": "Préparer le PDF", "pdf.non": "Plus tard",
    "an.titre": "Analyse de situation", "an.texte": "Racontez ce qui s'est passé : AMENA prépare une note juridique, comme une avocate.", "an.placeholder": "Depuis quand, qui, quoi, où… (15 caractères minimum)",
    "an.lancer": "Analyser", "an.encours": "Analyse en cours…", "an.court": "Décrivez la situation en quelques phrases.", "an.qualif": "Ce que dit la loi", "an.etapes": "Les étapes", "an.preuves": "Les preuves à réunir",
    "an.savoir": "À savoir", "an.questions": "Pour préciser", "an.chat": "Continuer dans le chat", "an.aucune": "Aucune situation type reconnue : décrivez plus précisément, ou posez la question dans le chat.",
    "lois.titre": "Bibliothèque des lois", "lois.texte": "Constitution, codes et lois tunisiennes, article par article.", "lois.placeholder": "Rechercher : licenciement, terre, vol…",
    "lois.textes": "Les textes", "lois.resultats": "Résultats", "lois.retour": "← Retour", "lois.aucun": "Aucun article trouvé.", "lois.art": "Art.",
    "aide.titre": "Aide et urgences", "aide.texte": "Appels gratuits. En danger immédiat, appelez d'abord la police ou la garde nationale.", "aide.urgences": "Urgences", "aide.ecoute": "Écoute", "aide.publics": "Services publics", "aide.assoc": "Associations",
    "dos.titre": "Dossier pour mon avocat(e)", "dos.texte": "Relisez et complétez, puis enregistrez en PDF (Imprimer → Enregistrer en PDF). Rien n'est envoyé ni enregistré.",
    "dos.faits": "Résumé des faits", "dos.analyse": "Analyse juridique", "dos.imprimer": "Enregistrer en PDF", "dos.vide": "Commencez par décrire votre situation dans le chat.",
    "avert": "AMENA informe et oriente ; elle ne remplace pas un avocat.", "confidentialite": "Confidentialité", "installer": "Installer l'application (Android, iPhone)",
  },
  ar: {
    "nav.accueil": "الرئيسية", "nav.chat": "تحدث", "nav.analyse": "تحليل", "nav.lois": "القوانين", "nav.aide": "مساعدة",
    "ac.titre": "محاميتك في جيبك", "ac.texte": "اطرح سؤالك القانوني بكلماتك، بالعربية أو بالفرنسية أو بالدارجة. أمانة تشرح لك القانون التونسي والإجراءات. مجانا وبسرية.",
    "ac.parler": "تحدث مع أمانة", "ac.domaines": "اختر موضوعا", "ac.urgence": "في خطر؟ اتصل بالرقم 197 (الشرطة) أو 190 (الإسعاف).", "ac.appeler": "اتصل",
    "chat.vide.t": "ماذا يحدث؟", "chat.vide.d": "صف وضعيتك: أمانة تذكر الفصول القانونية والخطوات والأدلة، ثم تطرح عليك أسئلة للتعمق.",
    "chat.placeholder": "اكتب رسالتك…", "chat.envoyer": "إرسال", "chat.reflexion": "أمانة تفكر…", "chat.sources": "المصادر",
    "chat.erreur": "الخادم لا يجيب. تثبت من الاتصال ثم أعد المحاولة.", "chat.nouveau": "محادثة جديدة",
    "pdf.q": "هل تريد أن أعد ملفك بصيغة PDF لمحاميك؟", "pdf.oui": "إعداد ملف PDF", "pdf.non": "لاحقا",
    "an.titre": "تحليل الوضعية", "an.texte": "احك ما حدث: أمانة تعد مذكرة قانونية كما تفعل المحامية.", "an.placeholder": "منذ متى، من، ماذا، أين… (15 حرفا على الأقل)",
    "an.lancer": "تحليل", "an.encours": "جار التحليل…", "an.court": "صف الوضعية في بضع جمل.", "an.qualif": "ماذا يقول القانون", "an.etapes": "الخطوات", "an.preuves": "الأدلة",
    "an.savoir": "ما يجب معرفته", "an.questions": "للتوضيح", "an.chat": "المواصلة في المحادثة", "an.aucune": "لم يتم التعرف على وضعية نموذجية: وضّح أكثر أو اطرح السؤال في المحادثة.",
    "lois.titre": "مكتبة القوانين", "lois.texte": "الدستور والمجلات والقوانين التونسية، فصلا بفصل.", "lois.placeholder": "ابحث: طرد، أرض، سرقة…",
    "lois.textes": "النصوص", "lois.resultats": "النتائج", "lois.retour": "→ رجوع", "lois.aucun": "لم يتم العثور على أي فصل.", "lois.art": "الفصل",
    "aide.titre": "المساعدة والطوارئ", "aide.texte": "مكالمات مجانية. في خطر فوري اتصل أولا بالشرطة أو بالحرس الوطني.", "aide.urgences": "الطوارئ", "aide.ecoute": "الإصغاء", "aide.publics": "الخدمات العمومية", "aide.assoc": "الجمعيات",
    "dos.titre": "ملف لمحاميّ", "dos.texte": "راجع وأكمل، ثم احفظ بصيغة PDF (طباعة ← حفظ PDF). لا يتم إرسال أو حفظ أي شيء.",
    "dos.faits": "ملخص الوقائع", "dos.analyse": "التحليل القانوني", "dos.imprimer": "حفظ بصيغة PDF", "dos.vide": "ابدأ بوصف وضعيتك في المحادثة.",
    "avert": "أمانة تعلم وتوجه ولا تعوض المحامي.", "confidentialite": "سياسة الخصوصية", "installer": "تثبيت التطبيق (أندرويد، آيفون)",
  },
};
const etat = { langue: "fr", messages: [], enCours: false, brouillon: "", derniereExpertise: null };
const t = (cle) => T[etat.langue][cle] ?? T.fr[cle] ?? cle;

// --- Petits outils DOM (jamais d'innerHTML pour du contenu venu du serveur) -----------------------------
function h(balise, attributs = {}, ...enfants) {
  const el = document.createElement(balise);
  for (const [k, v] of Object.entries(attributs || {})) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "string") el.setAttribute("style", v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const e of enfants.flat()) if (e != null && e !== false) el.append(e);
  return el;
}

function enLigne(texte) {
  const frag = document.createDocumentFragment();
  const motif = /(\*\*[^*]+\*\*|\[[^\]]+\]\((https?:\/\/[^)\s]+)\)|\*[^*\s][^*]*\*)/g;
  let dernier = 0;
  for (const m of texte.matchAll(motif)) {
    if (m.index > dernier) frag.append(texte.slice(dernier, m.index));
    const j = m[0];
    if (j.startsWith("**")) frag.append(h("strong", {}, j.slice(2, -2)));
    else if (j.startsWith("[")) frag.append(h("a", { href: m[2], target: "_blank", rel: "noopener noreferrer" }, j.slice(1, j.indexOf("]"))));
    else frag.append(h("em", {}, j.slice(1, -1)));
    dernier = m.index + j.length;
  }
  if (dernier < texte.length) frag.append(texte.slice(dernier));
  return frag;
}

function markdown(texte) {
  const racine = h("div", { class: "md" });
  let liste = null, para = [];
  const fermer = () => { if (para.length) { racine.append(h("p", { dir: "auto" }, enLigne(para.join(" ")))); para = []; } };
  for (const brute of texte.split("\n")) {
    const l = brute.trim();
    if (!l) { fermer(); liste = null; continue; }
    const titre = l.match(/^#{1,4}\s+(.*)/), puce = l.match(/^[-•]\s+(.*)/), num = l.match(/^\d+[.)]\s+(.*)/), cit = l.match(/^>\s?(.*)/);
    if (titre) { fermer(); liste = null; racine.append(h("h3", { dir: "auto" }, enLigne(titre[1]))); }
    else if (cit) { fermer(); liste = null; racine.append(h("blockquote", { dir: "auto" }, enLigne(cit[1]))); }
    else if (puce || num) {
      fermer();
      const genre = puce ? "ul" : "ol";
      if (!liste || liste.tagName.toLowerCase() !== genre) { liste = h(genre); racine.append(liste); }
      liste.append(h("li", { dir: "auto" }, enLigne((puce || num)[1])));
    } else { liste = null; para.push(l); }
  }
  fermer();
  return racine;
}

async function api(chemin, options) {
  const r = await fetch(API + chemin, options);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}
const envoyerJson = (chemin, corps) => api(chemin, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corps) });

// --- Navigation ------------------------------------------------------------------------------------
const ecran = document.getElementById("ecran");
const ECRANS = { accueil, chat, analyse, lois, aide, dossier };

function aller(nom) { location.hash = `#/${nom}`; }

function afficher() {
  const [nom, ...reste] = location.hash.replace(/^#\/?/, "").split("/");
  const page = ECRANS[nom] ? nom : "accueil";
  document.querySelectorAll(".onglets button").forEach((b) => { if (b.dataset.aller === page) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); });
  ecran.replaceChildren();
  const parametre = decodeURIComponent(reste.join("/"));
  // Lien « question » (#/chat/<question>) : la question est posée à l'ouverture, pour partager un exemple.
  if (page === "chat" && parametre && !etat.messages.length && !etat.enCours) {
    history.replaceState(null, "", "#/chat");
    setTimeout(() => envoyer(parametre.slice(0, 500)), 0);
  }
  ECRANS[page](ecran, parametre);
  document.querySelector(".compose")?.remove();
  if (page === "chat") ecran.after(composer());
  window.scrollTo(0, page === "chat" ? document.body.scrollHeight : 0);
}

function traduireNavigation() {
  document.documentElement.lang = etat.langue;
  document.documentElement.dir = etat.langue === "ar" ? "rtl" : "ltr";
  document.querySelectorAll("[data-t]").forEach((e) => { e.textContent = t(e.dataset.t); });
  document.getElementById("bouton-langue").textContent = etat.langue === "ar" ? "Fr" : "ع";
}

// --- Accueil ---------------------------------------------------------------------------------------
const DOMAINES = [
  { fr: ["Travail", "Licenciement, salaire"], ar: ["الشغل", "الطرد، الأجر"], photo: "avenue-bourguiba-tunis.webp",
    q: { fr: "Mon employeur m'a licencié sans préavis après cinq ans de travail. Quels sont mes droits ?", ar: "طردني المؤجر دون سابق إعلام بعد خمس سنوات عمل. ما هي حقوقي؟" } },
  { fr: ["Terres et biens", "Titre foncier, héritage"], ar: ["الأراضي والأملاك", "رسم عقاري، إرث"], photo: "oliveraie-dahar.webp",
    q: { fr: "J'ai une terre depuis 15 ans et j'ai appris qu'elle a un autre propriétaire. Que faire ?", ar: "عندي أرض منذ 15 سنة وعلمت أن لها مالكا آخر. ماذا أفعل؟" } },
  { fr: ["Argent et contrats", "Dette, arnaque, vol"], ar: ["المال والعقود", "دين، تحيل، سرقة"], photo: "marteau-portrait.webp",
    q: { fr: "J'ai prêté 2000 dinars à un voisin et il refuse de me rembourser. Que faire ?", ar: "أقرضت جاري 2000 دينار ويرفض إرجاعها. ماذا أفعل؟" } },
  { fr: ["Famille", "Divorce, garde, pension"], ar: ["الأسرة", "طلاق، حضانة، نفقة"], photo: "livres-marteau.webp",
    q: { fr: "Je veux divorcer et obtenir la garde des enfants. Comment se passe la procédure ?", ar: "أريد الطلاق والحصول على حضانة الأطفال. كيف تتم الإجراءات؟" } },
  { fr: ["Violences", "Plainte, protection"], ar: ["العنف", "شكاية، حماية"], photo: "justice-livre.webp",
    q: { fr: "Mon conjoint me frappe et m'insulte depuis des mois. Que puis-je faire ?", ar: "قريني يضربني ويشتمني منذ أشهر. ماذا يمكنني أن أفعل؟" } },
  { fr: ["Police et tribunal", "Accusé, convoqué, témoin"], ar: ["الشرطة والمحكمة", "متهم، استدعاء، شاهد"], photo: "palais-justice-tunis.webp",
    q: { fr: "On m'accuse d'un vol que je n'ai pas commis. Comment me défendre ?", ar: "اتهموني بسرقة لم أرتكبها. كيف أدافع عن نفسي؟" } },
];

function accueil(racine) {
  racine.append(
    h("section", { class: "heros", style: `--photo:url('${PHOTOS}/palais-justice-tunis.webp')` },
      h("h1", {}, t("ac.titre")), h("p", {}, t("ac.texte")),
      h("button", { class: "gros-bouton clair", onclick: () => aller("chat") }, t("ac.parler"), " →")),
    h("h2", {}, t("ac.domaines")),
    h("div", { class: "grille-domaines" }, ...DOMAINES.map((d) =>
      h("button", { class: "domaine", style: `--photo:url('${PHOTOS}/${d.photo}')`, onclick: () => { etat.messages = []; aller("chat"); setTimeout(() => envoyer(d.q[etat.langue] || d.q.fr), 50); } },
        h("strong", {}, (d[etat.langue] || d.fr)[0]), h("span", {}, (d[etat.langue] || d.fr)[1])))),
    h("div", { class: "urgence-bandeau" }, h("span", {}, t("ac.urgence")),
      h("a", { class: "gros-bouton", href: "tel:197", style: "width:auto;padding:0 18px;min-height:44px" }, t("ac.appeler"))),
    h("a", { class: "gros-bouton contour", href: "telecharger.html", style: "margin-top:14px" }, "📲 ", t("installer")),
    h("p", { class: "avert" }, t("avert"), " · ", h("a", { href: "confidentialite.html" }, t("confidentialite"))));
}

// --- Chat --------------------------------------------------------------------------------------------
function chat(racine) {
  const fil = h("div", { class: "fil", "aria-live": "polite" });
  if (!etat.messages.length) {
    fil.append(h("div", { class: "vide" }, h("h1", {}, t("chat.vide.t")), h("p", {}, t("chat.vide.d"))));
  } else {
    racine.append(h("button", { class: "retour", onclick: () => { etat.messages = []; afficher(); } }, "＋ ", t("chat.nouveau")));
  }
  etat.messages.forEach((m, i) => fil.append(vueMessage(m, i === etat.messages.length - 1)));
  racine.append(fil);
}

function vueMessage(m, dernier) {
  if (m.role === "user") return h("div", { class: "bulle-moi", dir: "auto" }, m.texte);
  const bloc = h("div", { class: "msg-ia" }, h("div", { class: "entete-ia" }, h("span", { class: "pastille-ia" }, "A"), "AMENA"));
  if (m.erreur) bloc.append(h("p", { class: "sous" }, t("chat.erreur")));
  else if (!m.texte) bloc.append(h("p", { class: "reflexion" }, t("chat.reflexion")));
  else bloc.append(markdown(m.texte));
  const meta = m.meta;
  if (meta && !m.enCours) {
    if (meta.sources?.length) {
      bloc.append(h("details", { class: "sources" }, h("summary", {}, `${t("chat.sources")} (${meta.sources.length})`),
        h("ol", {}, ...meta.sources.map((s) => h("li", { dir: "auto" }, s.titre)))));
    }
    if (dernier && meta.proposer_dossier && meta.expertise) {
      bloc.append(h("div", { class: "carte-pdf" }, h("strong", {}, t("pdf.q")),
        h("div", { class: "boutons" },
          h("button", { class: "gros-bouton", onclick: () => aller("dossier") }, t("pdf.oui")),
          h("button", { class: "gros-bouton contour", onclick: (e) => e.currentTarget.closest(".carte-pdf").remove() }, t("pdf.non")))));
    }
    if (dernier && meta.suggestions?.length) {
      bloc.append(h("div", { class: "puces" }, ...meta.suggestions.map((s) => h("button", { dir: "auto", onclick: () => envoyer(s) }, s))));
    }
  }
  return bloc;
}

function composer() {
  const zone = h("textarea", { rows: 1, placeholder: t("chat.placeholder"), dir: "auto", "aria-label": t("chat.placeholder") });
  zone.value = etat.brouillon;
  const bouton = h("button", { "aria-label": t("chat.envoyer"), disabled: etat.enCours }, etat.langue === "ar" ? "←" : "→");
  const partir = () => { const v = zone.value.trim(); if (v && !etat.enCours) { etat.brouillon = ""; envoyer(v); } };
  zone.addEventListener("input", () => { etat.brouillon = zone.value; zone.style.height = "auto"; zone.style.height = `${Math.min(zone.scrollHeight, 140)}px`; });
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); partir(); } });
  bouton.addEventListener("click", partir);
  return h("form", { class: "compose", onsubmit: (e) => { e.preventDefault(); partir(); } }, zone, bouton);
}

let rafraichissement = 0;
function redessinerChat() {
  if (!location.hash.startsWith("#/chat")) return;
  cancelAnimationFrame(rafraichissement);
  rafraichissement = requestAnimationFrame(() => {
    const fil = ecran.querySelector(".fil");
    if (!fil) return afficher();
    fil.replaceChildren(...etat.messages.map((m, i) => vueMessage(m, i === etat.messages.length - 1)));
    const b = document.querySelector(".compose button"); if (b) b.disabled = etat.enCours;
    window.scrollTo(0, document.body.scrollHeight);
  });
}

async function envoyer(texte) {
  if (etat.enCours) return;
  if (!location.hash.startsWith("#/chat")) aller("chat");
  const historique = etat.messages.filter((m) => m.texte && !m.erreur).slice(-8)
    .map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.texte }));
  etat.messages.push({ role: "user", texte });
  const reponse = { role: "ia", texte: "", meta: null, enCours: true };
  etat.messages.push(reponse);
  etat.enCours = true;
  if (ecran.querySelector(".vide")) afficher(); else redessinerChat();
  try {
    const r = await fetch(`${API}/chat/flux`, { method: "POST", headers: { "Content-Type": "application/json" },
                                                body: JSON.stringify({ message: texte, historique }) });
    if (r.status === 429) {  // trop de questions d'affilée : message clair au lieu d'une erreur
      const j = await r.json().catch(() => ({}));
      reponse.texte = (etat.langue === "ar" ? j.detail_ar : j.detail) || j.detail || "Patientez une minute.";
      return;
    }
    if (!r.ok || !r.body) throw new Error(`HTTP ${r.status}`);
    const lecteur = r.body.getReader(), decodeur = new TextDecoder();
    let tampon = "";
    for (;;) {
      const { value, done } = await lecteur.read();
      if (done) break;
      tampon += decodeur.decode(value, { stream: true });
      const blocs = tampon.split("\n\n");
      tampon = blocs.pop();
      for (const bloc of blocs) {
        const ligne = bloc.split("\n").find((l) => l.startsWith("data: "));
        if (!ligne) continue;
        const ev = JSON.parse(ligne.slice(6));
        if (ev.type === "meta") { reponse.meta = ev; if (ev.expertise) etat.derniereExpertise = ev.expertise; }
        else if (ev.type === "texte") { reponse.texte += ev.delta; redessinerChat(); }
        else if (ev.type === "fin") { reponse.texte = ev.reponse || reponse.texte; }
      }
    }
  } catch (erreur) {
    reponse.erreur = true;
  } finally {
    reponse.enCours = false;
    etat.enCours = false;
    redessinerChat();
  }
}

// --- Analyse -------------------------------------------------------------------------------------------
function analyse(racine) {
  const zone = h("textarea", { class: "champ", placeholder: t("an.placeholder"), dir: "auto" });
  const resultat = h("div");
  const bouton = h("button", { class: "gros-bouton", style: "margin-top:10px" }, t("an.lancer"));
  bouton.addEventListener("click", async () => {
    const situation = zone.value.trim();
    if (situation.length < 15) { resultat.replaceChildren(h("p", { class: "sous" }, t("an.court"))); return; }
    bouton.disabled = true; resultat.replaceChildren(h("p", { class: "reflexion" }, t("an.encours")));
    try {
      const a = await envoyerJson("/analyse", { situation, pays: "TN" });
      etat.derniereExpertise = { situations: a.qualifications.map((q) => q.libelle), analyse: a, faits: situation };
      resultat.replaceChildren(vueAnalyse(a, situation));
    } catch { resultat.replaceChildren(h("p", { class: "sous" }, t("chat.erreur"))); }
    bouton.disabled = false;
  });
  racine.append(h("h1", {}, t("an.titre")), h("p", { class: "sous" }, t("an.texte")), zone, bouton, resultat);
}

function vueAnalyse(a, situation) {
  if (!a.qualifications?.length) return h("p", { class: "vide" }, t("an.aucune"));
  const section = (titre, items) => items?.length ? [h("h2", {}, titre), h("ul", { class: "md" }, ...items.map((x) => h("li", { dir: "auto" }, x)))] : [];
  return h("div", {},
    h("h2", {}, t("an.qualif")),
    ...a.qualifications.map((q) => h("div", { class: "carte" }, h("h3", { dir: "auto" }, q.libelle), h("p", { dir: "auto" }, q.qualification),
      ...q.fondements.map((f) => h("p", { class: "meta", dir: "auto" }, h("strong", {}, `${t("lois.art")} ${f.article} · `), f.explication || f.contenu.slice(0, 260))))),
    ...section(t("an.etapes"), a.demarches),
    ...section(t("an.preuves"), a.preuves),
    ...section(t("an.savoir"), [...(a.delais || []), ...(a.vigilance || [])]),
    ...section(t("an.questions"), a.questions),
    a.synthese ? markdown(a.synthese) : null,
    h("button", { class: "gros-bouton", style: "margin-top:14px", onclick: () => { etat.messages = []; aller("chat"); setTimeout(() => envoyer(situation), 50); } }, t("an.chat")),
    h("button", { class: "gros-bouton contour", style: "margin-top:8px", onclick: () => aller("dossier") }, t("pdf.oui")));
}

// --- Lois ----------------------------------------------------------------------------------------------
async function lois(racine, param) {
  if (param) return detailTexte(racine, param);
  const champ = h("input", { class: "champ", type: "search", placeholder: t("lois.placeholder"), dir: "auto", "aria-label": t("lois.placeholder") });
  const zone = h("div");
  racine.append(h("h1", {}, t("lois.titre")), h("p", { class: "sous" }, t("lois.texte")), champ, zone);
  let minuterie;
  champ.addEventListener("input", () => {
    clearTimeout(minuterie);
    minuterie = setTimeout(async () => {
      const q = champ.value.trim();
      if (q.length < 2) return listeTextes(zone);
      try {
        const res = await api(`/lois/recherche?q=${encodeURIComponent(q)}&pays=TN`);
        zone.replaceChildren(h("h2", {}, t("lois.resultats")), ...(res.length ? res.map((r) =>
          h("button", { class: "carte", style: "display:block;width:100%;text-align:start", onclick: () => aller(`lois/${r.texte_id}`) },
            h("h3", { dir: "auto" }, `${t("lois.art")} ${r.numero}`), h("p", { class: "meta", dir: "auto" }, r.texte_titre),
            h("p", { dir: "auto" }, r.contenu.slice(0, 220) + (r.contenu.length > 220 ? "…" : "")))) : [h("p", { class: "vide" }, t("lois.aucun"))]));
      } catch { zone.replaceChildren(h("p", { class: "sous" }, t("chat.erreur"))); }
    }, 300);
  });
  listeTextes(zone);
}

async function listeTextes(zone) {
  try {
    const textes = await api("/lois?pays=TN");
    textes.sort((a, b) => (b.id.startsWith("tn-off-") - a.id.startsWith("tn-off-")));
    zone.replaceChildren(h("h2", {}, t("lois.textes")), ...textes.map((x) =>
      h("button", { class: "carte", style: "display:block;width:100%;text-align:start", onclick: () => aller(`lois/${x.id}`) },
        h("h3", { dir: "auto" }, x.titre), h("p", { class: "meta", dir: "auto" }, x.reference || x.type))));
  } catch { zone.replaceChildren(h("p", { class: "sous" }, t("chat.erreur"))); }
}

async function detailTexte(racine, id) {
  racine.append(h("button", { class: "retour", onclick: () => aller("lois") }, t("lois.retour")));
  try {
    const x = await api(`/lois/${encodeURIComponent(id)}`);
    const filtre = h("input", { class: "champ", type: "search", placeholder: t("lois.placeholder"), dir: "auto" });
    const liste = h("div");
    const dessiner = () => {
      const q = filtre.value.trim().toLowerCase();
      const arts = x.articles.filter((a) => !q || `${a.numero} ${a.titre} ${a.contenu}`.toLowerCase().includes(q)).slice(0, 80);
      liste.replaceChildren(...arts.map((a) => h("div", { class: "carte" }, h("h3", { dir: "auto" }, `${t("lois.art")} ${a.numero}${a.titre ? " · " + a.titre : ""}`),
        h("p", { dir: "auto" }, a.contenu))));
    };
    filtre.addEventListener("input", dessiner);
    racine.append(h("h1", { dir: "auto", style: "font-size:1.4rem" }, x.titre), h("p", { class: "sous", dir: "auto" }, x.reference || ""),
      x.resume ? h("p", { dir: "auto" }, x.resume) : null, filtre, liste);
    dessiner();
  } catch { racine.append(h("p", { class: "sous" }, t("chat.erreur"))); }
}

// --- Aide ----------------------------------------------------------------------------------------------
async function aide(racine) {
  racine.append(h("h1", {}, t("aide.titre")), h("p", { class: "sous" }, t("aide.texte")));
  try {
    const r = await api("/ressources");
    const lg = etat.langue;
    const numeros = (titre, items) => items?.length ? [h("h2", {}, titre), h("div", { class: "liste-numeros" }, ...items.map((n) =>
      h(n.numero ? "a" : "div", { class: "numero", href: n.numero ? `tel:${n.numero}` : null },
        n.numero ? h("b", {}, n.numero) : null,
        h("span", {}, h("strong", {}, n[lg] || n.fr || n[`nom_${lg}`] || n.nom_fr), h("small", {}, n[`detail_${lg}`] || n.detail_fr || n[`services_${lg}`] || n.services_fr || "")))))] : [];
    racine.append(...numeros(t("aide.urgences"), r.urgences), ...numeros(t("aide.ecoute"), r.ecoute),
                  ...numeros(t("aide.publics"), r.publics), ...numeros(t("aide.assoc"), r.associations));
  } catch { racine.append(h("p", { class: "sous" }, t("chat.erreur"))); }
}

// --- Dossier imprimable ---------------------------------------------------------------------------------
function dossier(racine) {
  const faits = etat.messages.filter((m) => m.role === "user").map((m) => m.texte).join("\n\n") || etat.derniereExpertise?.faits || "";
  const a = etat.derniereExpertise?.analyse;
  racine.append(h("h1", {}, t("dos.titre")), h("p", { class: "sous no-print" }, t("dos.texte")));
  if (!faits && !a) { racine.append(h("p", { class: "vide" }, t("dos.vide"))); return; }
  racine.append(h("h2", {}, t("dos.faits")), h("textarea", { class: "champ", dir: "auto", "aria-label": t("dos.faits") }, faits));
  if (a?.qualifications?.length) {
    racine.append(h("h2", {}, t("dos.analyse")), vueAnalysePourDossier(a));
  }
  racine.append(h("button", { class: "gros-bouton no-print", style: "margin-top:16px", onclick: () => window.print() }, t("dos.imprimer")),
                h("p", { class: "avert" }, t("avert")));
}

function vueAnalysePourDossier(a) {
  const liste = (titre, items) => items?.length ? [h("h3", {}, titre), h("ul", {}, ...items.map((x) => h("li", { dir: "auto" }, x)))] : [];
  return h("div", { class: "md" },
    ...a.qualifications.flatMap((q) => [h("h3", { dir: "auto" }, q.libelle), h("p", { dir: "auto" }, q.qualification),
      h("ul", {}, ...q.fondements.map((f) => h("li", { dir: "auto" }, `${f.texte} — ${t("lois.art")} ${f.article}`)))]),
    ...liste(t("an.etapes"), a.demarches), ...liste(t("an.preuves"), a.preuves),
    ...liste(t("an.savoir"), [...(a.delais || []), ...(a.vigilance || [])]), ...liste(t("an.questions"), a.questions));
}

// --- Démarrage -------------------------------------------------------------------------------------------
document.querySelectorAll("[data-aller]").forEach((b) => b.addEventListener("click", () => aller(b.dataset.aller)));
document.getElementById("bouton-langue").addEventListener("click", () => {
  etat.langue = etat.langue === "fr" ? "ar" : "fr";
  traduireNavigation();
  afficher();
});
// Sortie rapide : la page est remplacée (pas de retour possible) par une recherche météo.
document.getElementById("bouton-sortie").addEventListener("click", () => location.replace("https://www.google.com/search?q=m%C3%A9t%C3%A9o+tunis"));
window.addEventListener("hashchange", afficher);
if (navigator.language?.startsWith("ar")) etat.langue = "ar";
traduireNavigation();
afficher();

// Application installable (PWA) : seul le squelette de l'interface est mis en cache, jamais les réponses.
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
