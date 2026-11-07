// Conversation avec AMENA, mise en page d'un assistant moderne :
//   - barre de navigation en haut (discussions, titre, état, nouvelle discussion) ;
//   - messages de l'utilisatrice en bulle, réponses d'AMENA en texte libre ;
//   - animation de réflexion (balance qui oscille, étape en cours qui miroite), repliée ensuite ;
//   - réponses diffusées en direct (Server-Sent Events), chaque mot apparaissant en fondu ;
//   - Markdown, citations [n] reliées aux sources, questions de suivi, copier, écouter, régénérer ;
//   - plusieurs discussions, en mémoire uniquement (rien dans le navigateur ni sur le serveur).

import { langueCourante, t } from "../i18n.js";
import { rendreMarkdown, texteBrut } from "../markdown.js";
import { api, h, icone } from "../ui.js";
import { preparerDossier } from "./dossier.js";

const etat = { conversations: [], courante: null, enCours: false, controleur: null, brouillon: "" };
const Reconnaissance = window.SpeechRecognition || window.webkitSpeechRecognition;
const VOIX = { fr: "fr-FR", ar: "ar-SA", dz: "fr-FR" };
const DUREE_FONDU = 450;  // ms : durée d'apparition d'un mot

export function preremplir(texte) { etat.brouillon = texte; }

const conversation = () => etat.conversations.find((c) => c.id === etat.courante);

function nouvelleConversation() {
  const c = { id: crypto.randomUUID(), titre: t("chat2.nouvelle"), messages: [] };
  etat.conversations.unshift(c);
  etat.courante = c.id;
  return c;
}

const historiqueDe = (c) => c.messages.filter((m) => m.texte && (m.role === "user" || m.fini))
  .map((m) => ({ role: m.role, content: m.texte }));

// --- Lecture du flux SSE -----------------------------------------------------------
async function lireFlux(reponse, surEvenement) {
  const lecteur = reponse.body.getReader();
  const decodeur = new TextDecoder();
  let tampon = "";
  for (;;) {
    const { value, done } = await lecteur.read();
    if (done) break;
    tampon += decodeur.decode(value, { stream: true });
    const blocs = tampon.split("\n\n");
    tampon = blocs.pop();
    for (const bloc of blocs) {
      const ligne = bloc.split("\n").find((l) => l.startsWith("data: "));
      if (ligne) surEvenement(JSON.parse(ligne.slice(6)));
    }
  }
}

// --- Fondu des mots qui arrivent ------------------------------------------------------
// Le Markdown est reconstruit à chaque image. Pour que l'animation ne reparte pas de zéro,
// on note quand chaque portion du texte est apparue (des « jalons » : début, fin, instant) et on
// enveloppe les portions récentes dans un <span> dont l'animation est décalée d'autant.
function animerArrivee(corps, m) {
  const maintenant = performance.now();
  const marcheur = document.createTreeWalker(corps, NodeFilter.SHOW_TEXT);
  const noeuds = [];
  let total = 0;
  while (marcheur.nextNode()) {
    noeuds.push([marcheur.currentNode, total]);
    total += marcheur.currentNode.data.length;
  }
  m.jalons = m.jalons || [];
  m.vu = Math.min(m.vu || 0, total);
  if (total > m.vu) { m.jalons.push([m.vu, total, maintenant]); m.vu = total; }
  m.jalons = m.jalons.filter(([, , instant]) => maintenant - instant < DUREE_FONDU);
  if (!m.jalons.length) return;
  for (const [noeud, debutNoeud] of noeuds.reverse()) {
    const longueur = noeud.data.length;
    for (const [debut, fin, instant] of [...m.jalons].reverse()) {
      const a = Math.max(debut, debutNoeud) - debutNoeud;
      const b = Math.min(fin, debutNoeud + longueur) - debutNoeud;
      if (a >= b || !noeud.parentNode) continue;
      if (b < noeud.data.length) noeud.splitText(b);
      const milieu = a > 0 ? noeud.splitText(a) : noeud;
      const span = document.createElement("span");
      span.className = "mot-neuf";
      span.style.animationDelay = `${Math.round(instant - maintenant)}ms`;
      milieu.replaceWith(span);
      span.append(milieu);
    }
  }
}

export function pageChat(racine) {
  if (!conversation()) nouvelleConversation();

  const fil = h("div", { class: "chat-fil", role: "log", "aria-live": "polite" });
  // On ne suit le bas du fil que si l'utilisatrice y est déjà : si elle remonte pour lire,
  // la réponse en cours ne la ramène pas de force en bas.
  let suivreBas = true;
  fil.addEventListener("scroll", () => {
    suivreBas = fil.scrollHeight - fil.scrollTop - fil.clientHeight < 90;
  }, { passive: true });
  const defiler = (force = false) => {
    if (force || suivreBas) fil.scrollTop = fil.scrollHeight;
  };
  const liste = h("div", { class: "chat-liste", role: "list" });
  const titre = h("h1", { class: "chat-titre", dir: "auto" });
  const champ = h("textarea", { rows: 1, dir: "auto", placeholder: t("chat.placeholder"), "aria-label": t("chat.placeholder") });
  const bouton = h("button", { class: "chat-envoyer", type: "submit", "aria-label": t("chat.envoyer") });

  // --- Rendu d'un message ----------------------------------------------------------
  function vueUtilisatrice(m, index, c) {
    const estDernier = index === c.messages.map((x) => x.role).lastIndexOf("user");
    return h("div", { class: `msg msg-moi${entree(m)}` },
      h("div", { class: "bulle-moi", dir: "auto" }, m.texte),
      estDernier && !etat.enCours ? h("button", { class: "msg-modifier", type: "button", title: t("chat2.modifier"),
        "aria-label": t("chat2.modifier"),
        onclick: () => { champ.value = m.texte; c.messages.splice(index); dessiner(); champ.focus(); } }, icone("document")) : null);
  }

  // L'animation d'entrée ne se joue qu'une fois : le message est redessiné à chaque morceau reçu.
  const entree = (m) => (m.vu_une_fois ? "" : ((m.vu_une_fois = true), " entree"));
  const marque = (anime) => h("span", { class: `marque-ia${anime ? " anime" : ""}`, "aria-hidden": "true" }, icone("balance"));

  function vueReflexion(m) {
    const enReflexion = !m.fini && !m.texte;
    if (enReflexion) {
      const actuelle = m.etapes.at(-1) || t("chat3.reflexion");
      return h("div", { class: "reflexion active", role: "status" },
        marque(true),
        h("span", { class: "texte-miroir" }, actuelle),
        m.etapes.length > 1 ? h("ol", { class: "etapes-faites" },
          ...m.etapes.slice(0, -1).map((e) => h("li", {}, icone("liste"), e))) : null);
    }
    if (!m.etapes.length) return null;
    return h("details", { class: "reflexion repliee" },
      h("summary", {}, h("span", {}, `${t("chat2.reflexion")} · ${m.etapes.length} ${m.etapes.length === 1 && langueCourante() === "fr" ? t("chat2.etapes").replace(/s$/, "") : t("chat2.etapes")}`), icone("fleche", "icone chevron")),
      h("ol", {}, ...m.etapes.map((e) => h("li", {}, e))));
  }

  function vueIA(m, element = null) {
    const citer = (n) => h("button", { class: "cite", type: "button", title: m.meta?.sources[n - 1]?.titre || "",
      onclick: (e) => {
        const carte = e.currentTarget.closest(".msg").querySelector(`[data-source="${n}"]`);
        carte?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
        carte?.classList.add("eclaire");
        setTimeout(() => carte?.classList.remove("eclaire"), 1400);
      } }, String(n));

    const visible = m.fini ? m.texte : m.texte.slice(0, m.affiche || 0);
    const corps = h("div", { class: "msg-corps" }, visible ? rendreMarkdown(visible, citer) : null);
    if (visible) animerArrivee(corps, m);

    const d = m.meta;
    const vue = h("article", { class: `msg msg-ia${entree(m)}${d?.urgence ? " urgent" : ""}${m.fini ? "" : " en-direct"}` },
      vueReflexion(m),
      d?.urgence ? h("div", { class: "contacts-message" },
        ...d.contacts.map((c) => h("a", { href: `tel:${c.numero}` }, icone("aide"), `${c.numero} · ${c.nom}`))) : null,
      corps,
      m.interrompu ? h("p", { class: "discret" }, t("chat2.interrompu")) : null);

    // Pendant l'écriture, la marque d'AMENA s'anime sous le texte, comme une plume.
    if (!m.fini && m.texte) vue.append(h("div", { class: "msg-pied" }, marque(true)));

    if (m.fini && d) {
      if (d.sources.length) {
        vue.append(h("div", { class: "msg-sources" },
          ...d.sources.map((s, i) => h("a", { class: "carte-source", href: s.lien, "data-source": i + 1, dir: "auto",
                                               onclick: () => signal(m, true, 0.3, [s]) },
            h("span", { class: "num-source" }, i + 1),
            // « Art. Pénal — Aggravation des peines » → « Aggravation des peines » : on ne garde
            // « Art. » que devant un vrai numéro d'article.
            h("strong", {}, s.titre.split(" > ").slice(-1)[0].replace(/^Art\. (?!\d)[^—]*— /, "")),
            h("small", {}, s.titre.split(" > ")[0])))));
      }
      vue.append(h("div", { class: "msg-pied" },
        marque(false),
        h("div", { class: "msg-actions" },
          bouton_action("copier", "chat2.copier", async (e) => {
            // e.currentTarget vaut null après un await : on garde le bouton avant.
            const boutonCopie = e.currentTarget;
            await navigator.clipboard?.writeText(texteBrut(m.texte));
            if (!m.copie) { m.copie = true; signal(m, true, 0.5); }
            boutonCopie.classList.add("choisie");
            boutonCopie.title = t("chat2.copie");
          }),
          bouton_action("hautparleur", "chat.lire", () => lire(m.texte, d.langue)),
          bouton_action("rejouer", "chat2.regenerer", () => regenerer(), etat.enCours || m !== conversation().messages.at(-1)),
          bouton_action("pouce", "chat.utile", (e) => avis(m, true, e), false, m.avis === true),
          bouton_action("poucebas", "chat.pasutile", (e) => avis(m, false, e), false, m.avis === false)),
        h("span", { class: "msg-meta" },
          d.triage ? h("span", { class: `pastille ${d.urgence ? "danger" : ""}` }, t(`triage.${d.triage.label}`)) : null,
          m.mode && m.mode !== "conversation" ? h("span", {},
            t({ llm: "chat2.mode.llm", "llm-local": "chat2.mode.local" }[m.mode] || "chat2.mode.sources")) : null)));
      // Après les précisions, AMENA propose de préparer le PDF du dossier pour l'avocat(e).
      if (m === conversation().messages.at(-1) && d.proposer_dossier && d.expertise && !m.dossier_ecarte) {
        const preparer = () => preparerDossier({
          faits: conversation().messages.filter((x) => x.role === "user").map((x) => x.texte).join("\n"),
          analyse: d.expertise.analyse });
        vue.append(h("div", { class: "proposition-dossier", role: "group", "aria-label": t("chat3.pdf.q") },
          h("span", { class: "proposition-icone", "aria-hidden": "true" }, icone("document")),
          h("div", {}, h("strong", {}, t("chat3.pdf.q")), h("p", {}, t("chat3.pdf.d"))),
          h("div", { class: "proposition-boutons" },
            h("a", { href: "#/dossier", class: "bouton bouton-primaire", onclick: preparer }, t("chat3.pdf.oui")),
            h("button", { type: "button", class: "bouton bouton-contour",
                          onclick: () => { m.dossier_ecarte = true; dessiner(); } }, t("chat3.pdf.non")))));
      }
      if (m === conversation().messages.at(-1) && d.suggestions?.length) {
        vue.append(h("div", { class: "msg-suivis" },
          ...d.suggestions.map((q) => h("button", { type: "button", dir: "auto", onclick: () => envoyer(q) },
            icone("fleche", "icone icone-direction"), q)),
          // Situation analysée : on propose d'en faire un dossier pour l'avocat(e).
          d.expertise ? h("a", { href: "#/dossier", class: "suivi-action", onclick: () => preparerDossier({
            faits: conversation().messages.filter((x) => x.role === "user").map((x) => x.texte).join("\n"),
            analyse: d.expertise.analyse }) }, icone("document"), t("chat2.dossier")) : null,
          h("a", { href: "#/analyse", class: "suivi-action" }, icone("balance"), t("chat2.analyser"))));
      }
    }
    if (element) element.replaceWith(vue);
    return vue;
  }

  function bouton_action(nom, cle, action, desactive = false, choisi = false) {
    return h("button", { class: `action-icone${choisi ? " choisie" : ""}`, type: "button", title: t(cle), "aria-label": t(cle),
                         disabled: desactive, onclick: action }, icone(nom));
  }

  function avis(m, utile, e) {
    if (m.avis != null) return;
    m.avis = utile;
    e.currentTarget.classList.add("choisie");
    // Auto-apprentissage : seuls la clé de situation et les identifiants des sources partent.
    api("/api/avis", { method: "POST", body: { utile, cle: m.meta?.cle_apprentissage,
      sources: (m.meta?.sources || []).map((s) => s.id_apprentissage).filter(Boolean) } }).catch(() => {});
  }

  // Apprentissage implicite : AMENA apprend aussi de ce que fait l'utilisatrice, sans lui
  // demander d'avis. Ouvrir une source, copier une réponse = plutôt utile ; régénérer = pas utile.
  // Seuls la clé de situation et des identifiants de sources partent, jamais le texte.
  function signal(m, utile, poids, sources = m.meta?.sources || []) {
    const ids = sources.map((s) => s.id_apprentissage).filter(Boolean);
    if (!m.meta?.cle_apprentissage || !ids.length) return;
    api("/api/avis", { method: "POST", body: { utile, cle: m.meta.cle_apprentissage, sources: ids,
                                               implicite: true, poids } }).catch(() => {});
  }

  function lire(texte, langue) {
    if (!("speechSynthesis" in window)) return;
    speechSynthesis.cancel();
    const enonce = new SpeechSynthesisUtterance(texteBrut(texte));
    enonce.lang = VOIX[langue] || "fr-FR";
    speechSynthesis.speak(enonce);
  }

  // --- Écran d'accueil d'une discussion vide ----------------------------------------
  function accueil() {
    const heure = new Date().getHours();
    const salut = heure >= 18 || heure < 5 ? t("chat2.bonsoir") : t("chat2.bonjour");
    const cartes = [["document", "chat2.c1"], ["bouclier", "chat2.c2"], ["mallette", "chat2.c3"], ["globe", "chat2.c4"]];
    return h("section", { class: "chat-accueil" },
      h("h2", {}, marque(false), h("span", {}, `${salut}, ${t("chat2.je_suis")}`)),
      h("p", {}, t("chat2.accueil")),
      h("div", { class: "cartes-bienvenue" }, ...cartes.map(([nom, cle]) =>
        h("button", { type: "button", class: "carte-bienvenue", onclick: () => envoyer(t(`${cle}.q`)) },
          icone(nom), h("span", {}, t(`${cle}.t`))))),
      h("p", { class: "note-chat" }, icone("cadenas"), t("chat2.confidentiel")));
  }

  // --- Barre de navigation du chat ----------------------------------------------------------
  const historique = h("details", { class: "chat-historique" },
    h("summary", { title: t("chat2.discussions") }, icone("liste"), h("span", {}, t("chat2.discussions"))),
    h("div", { class: "chat-historique-menu" }, h("p", { class: "chat-rubrique" }, t("chat2.discussions")), liste,
      h("p", { class: "chat-ephemere" }, icone("cadenas"), t("chat2.ephemere"))));
  document.addEventListener("click", function fermer(e) {
    if (!historique.isConnected) { document.removeEventListener("click", fermer); return; }
    if (!historique.contains(e.target)) historique.open = false;
  });
  const boutonNouveau = h("button", { class: "chat-nouveau", type: "button", title: t("chat2.nouvelle"), onclick: () => {
    if (etat.enCours) return;
    if (conversation().messages.length) nouvelleConversation();
    dessiner();
    champ.focus();
  } }, h("span", { class: "plus", "aria-hidden": "true" }, "+"), h("span", {}, t("chat2.nouvelle")));

  // --- Dessin général ---------------------------------------------------------------
  function dessiner() {
    const c = conversation();
    titre.textContent = c.messages.length ? c.titre : t("chat.titre");
    fil.replaceChildren(...(c.messages.length
      ? c.messages.map((m, i) => (m.role === "user" ? vueUtilisatrice(m, i, c) : (m.el = vueIA(m))))
      : [accueil()]));
    fil.classList.toggle("vide", !c.messages.length);
    liste.replaceChildren(...etat.conversations.map((x) => h("div", { class: `chat-entree${x.id === etat.courante ? " active" : ""}`, role: "listitem" },
      h("button", { type: "button", class: "chat-entree-titre", dir: "auto", onclick: () => {
        if (etat.enCours) return;
        etat.courante = x.id; historique.open = false; dessiner();
      } }, h("span", {}, x.titre)),
      h("button", { type: "button", class: "chat-entree-suppr", title: t("chat2.supprimer"), "aria-label": t("chat2.supprimer"),
        onclick: () => {
          if (etat.enCours) return;
          etat.conversations = etat.conversations.filter((y) => y.id !== x.id);
          if (!etat.conversations.length) nouvelleConversation();
          if (!conversation()) etat.courante = etat.conversations[0].id;
          dessiner();
        } }, icone("corbeille")))));
    bouton.replaceChildren(icone(etat.enCours ? "carre" : "envoyer"));
    bouton.title = t(etat.enCours ? "chat2.arreter" : "chat.envoyer");
    bouton.classList.toggle("arret", etat.enCours);
    defiler();
  }

  // --- Envoi et diffusion ------------------------------------------------------------------
  async function envoyer(texte, { regeneration = false } = {}) {
    texte = (texte || "").trim();
    if (!texte || etat.enCours) return;
    const c = conversation();
    if (!regeneration) {
      if (!c.messages.length) c.titre = texte.length > 46 ? `${texte.slice(0, 46)}…` : texte;
      c.messages.push({ role: "user", texte });
    }
    const historiqueEnvoye = historiqueDe(c).slice(0, -1);  // tout sauf le message qu'on envoie
    const m = { role: "assistant", texte: "", affiche: 0, etapes: [], fini: false, meta: null, mode: null };
    c.messages.push(m);
    etat.enCours = true;
    etat.controleur = new AbortController();
    suivreBas = true;   // un nouvel envoi ramène toujours au bas du fil
    dessiner();
    defiler(true);

    let tamponFini = false;
    let boucle = false;
    const lancerFrappe = () => { if (!boucle) { boucle = true; requestAnimationFrame(frappe); } };
    const libelles = { analyse: t("chat2.e.analyse"), sources: t("chat2.e.sources"), redaction: t("chat2.e.redaction") };
    // Révélation progressive du texte reçu, à un rythme régulier qui accélère si le retard grandit.
    let derniere = 0;
    const frappe = (instant) => {
      if (m.affiche < m.texte.length && instant - derniere > 30) {
        derniere = instant;
        m.affiche += Math.max(3, Math.ceil((m.texte.length - m.affiche) / 18));
        m.el = vueIA(m, m.el);
        defiler();
      }
      if (tamponFini && m.affiche >= m.texte.length) {
        m.fini = true;
        etat.enCours = false;
        dessiner();
        return;
      }
      requestAnimationFrame(frappe);
    };

    try {
      const reponse = await fetch("/api/chat/flux", {
        method: "POST", headers: { "Content-Type": "application/json" }, signal: etat.controleur.signal,
        body: JSON.stringify({ message: texte, historique: historiqueEnvoye }),
      });
      if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`);
      lancerFrappe();
      await lireFlux(reponse, (ev) => {
        if (ev.type === "etape") {
          const libelle = ev.cle === "sources" ? `${libelles.sources} · ${ev.nombre} ${t("chat2.sources")}` : libelles[ev.cle];
          m.etapes.push(libelle);
          m.el = vueIA(m, m.el);
        } else if (ev.type === "meta") {
          m.meta = ev;
        } else if (ev.type === "texte") {
          m.texte += ev.delta;
        } else if (ev.type === "fin") {
          m.mode = ev.mode;
          m.texte = ev.reponse || m.texte;
        }
      });
      tamponFini = true;
    } catch (erreur) {
      if (erreur.name === "AbortError") {
        m.interrompu = true;
      } else {
        m.texte = t("chat.erreur");
        m.meta = m.meta || { urgence: true, triage: { label: "urgence" }, contacts: [{ numero: "197", nom: "Police" }, { numero: "1899", nom: "Numéro vert" }], sources: [], suggestions: [] };
      }
      tamponFini = true;
      lancerFrappe();
    }
  }

  function regenerer() {
    const c = conversation();
    if (etat.enCours || c.messages.at(-1)?.role !== "assistant") return;
    // Régénérer : la réponse ne convenait pas ; ses sources descendent un peu pour cette situation.
    signal(c.messages.at(-1), false, 0.5);
    c.messages.pop();
    const derniere = c.messages.at(-1);
    if (derniere?.role === "user") envoyer(derniere.texte, { regeneration: true });
  }

  // --- Compositeur -----------------------------------------------------------------------------
  const formulaire = h("form", { class: "compositeur", onsubmit: (e) => {
    e.preventDefault();
    if (etat.enCours) { etat.controleur?.abort(); return; }
    const texte = champ.value;
    champ.value = "";
    champ.style.height = "auto";
    envoyer(texte);
  } }, champ);
  const outils = h("div", { class: "compositeur-outils" });
  if (Reconnaissance) {
    const micro = h("button", { class: "action-icone", type: "button", title: t("chat.micro"), "aria-label": t("chat.micro") }, icone("micro"));
    let ecoute = null;
    micro.onclick = () => {
      if (ecoute) { ecoute.stop(); return; }
      ecoute = new Reconnaissance();
      ecoute.lang = langueCourante() === "ar" ? "ar-TN" : "fr-FR";
      ecoute.interimResults = true;
      micro.classList.add("ecoute");
      ecoute.onresult = (e) => { champ.value = Array.from(e.results, (r) => r[0].transcript).join(" "); };
      ecoute.onend = () => { ecoute = null; micro.classList.remove("ecoute"); champ.focus(); };
      ecoute.start();
    };
    outils.append(micro);
  }
  outils.append(h("span", { class: "astuce" }, t("chat2.astuce")), bouton);
  formulaire.append(outils);

  champ.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); formulaire.requestSubmit(); }
  });
  champ.addEventListener("input", () => { champ.style.height = "auto"; champ.style.height = `${Math.min(champ.scrollHeight, 220)}px`; });

  racine.append(h("div", { class: "chat-app" },
    h("header", { class: "chat-barre" },
      historique,
      titre,
      h("span", { class: "chat-statut" }, h("span", { class: "point-vert" }), t("chat2.enligne")),
      boutonNouveau),
    fil,
    h("div", { class: "compositeur-zone" }, formulaire,
      h("p", { class: "avertissement-chat" }, t("chat2.avertissement")))));

  dessiner();
  if (etat.brouillon) {
    const texte = etat.brouillon;
    etat.brouillon = "";
    if (conversation().messages.length) nouvelleConversation();
    envoyer(texte);
  } else {
    champ.focus({ preventScroll: true });
  }
}
