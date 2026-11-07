// Page « Installer AMENA » : bouton d'installation natif quand le navigateur le propose
// (Chrome, Edge, Samsung Internet). Fichier séparé pour respecter la politique de sécurité (CSP).
let invite = null;
const bouton = document.getElementById("installer");
window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); invite = e; bouton.style.display = "flex"; });
bouton.addEventListener("click", async () => {
  if (!invite) return;
  invite.prompt();
  await invite.userChoice;
  invite = null;
  bouton.style.display = "none";
});
if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});
