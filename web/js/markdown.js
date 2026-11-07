// Rendu Markdown léger et SÛR : construit des nœuds DOM (jamais d'innerHTML), si bien qu'aucun
// contenu venant du modèle ou des sources ne peut injecter de code dans la page.
// Pris en charge : ### titres, **gras**, *italique*, listes (- / 1.), paragraphes, citations [n].

function enLigne(texte, citer) {
  const fragment = document.createDocumentFragment();
  // Découpe en jetons : **gras**, *italique*, [n]
  const motif = /(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|\[\d{1,2}\])/g;
  let dernier = 0;
  for (const m of texte.matchAll(motif)) {
    if (m.index > dernier) fragment.append(texte.slice(dernier, m.index));
    const jeton = m[0];
    if (jeton.startsWith("**")) {
      const b = document.createElement("strong");
      b.textContent = jeton.slice(2, -2);
      fragment.append(b);
    } else if (jeton.startsWith("[")) {
      fragment.append(citer ? citer(Number(jeton.slice(1, -1))) : jeton);
    } else {
      const i = document.createElement("em");
      i.textContent = jeton.slice(1, -1);
      fragment.append(i);
    }
    dernier = m.index + jeton.length;
  }
  if (dernier < texte.length) fragment.append(texte.slice(dernier));
  return fragment;
}

export function rendreMarkdown(texte, citer = null) {
  const racine = document.createElement("div");
  racine.className = "md";
  let liste = null;
  let paragraphe = [];

  const fermerParagraphe = () => {
    if (!paragraphe.length) return;
    const p = document.createElement("p");
    p.dir = "auto";
    p.append(enLigne(paragraphe.join(" "), citer));
    racine.append(p);
    paragraphe = [];
  };

  for (const brute of texte.split("\n")) {
    const ligne = brute.trim();
    if (!ligne) { fermerParagraphe(); liste = null; continue; }
    const titre = ligne.match(/^(#{1,4})\s+(.*)/);
    const puce = ligne.match(/^[-•*]\s+(.*)/);
    const numero = ligne.match(/^\d+[.)]\s+(.*)/);
    if (titre) {
      fermerParagraphe(); liste = null;
      const h = document.createElement(titre[1].length <= 2 ? "h3" : "h4");
      h.dir = "auto";
      h.append(enLigne(titre[2], citer));
      racine.append(h);
    } else if (puce || numero) {
      fermerParagraphe();
      const genre = puce ? "UL" : "OL";
      if (!liste || liste.tagName !== genre) { liste = document.createElement(genre.toLowerCase()); racine.append(liste); }
      const li = document.createElement("li");
      li.dir = "auto";
      li.append(enLigne((puce || numero)[1], citer));
      liste.append(li);
    } else {
      liste = null;
      paragraphe.push(ligne);
    }
  }
  fermerParagraphe();
  return racine;
}

// Texte brut, sans marqueurs : pour copier ou lire à voix haute.
export const texteBrut = (texte) => texte.replace(/\*\*|\*|#{1,4}\s|\[\d{1,2}\]/g, "").replace(/\n{3,}/g, "\n\n").trim();
