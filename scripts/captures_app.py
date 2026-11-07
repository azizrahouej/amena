"""Captures d'écran de l'application mobile en ligne, en attendant la fin des réponses (Edge + protocole DevTools).

    python scripts/captures_app.py            → docs/linkedin/*.png (1080 × 2400)
"""
import base64, json, os, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request
from pathlib import Path

import websocket  # websocket-client

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "docs" / "linkedin"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "https://amena.onrender.com/mobile/"
PORT = 9333
ECRANS = [
    ("1-accueil", "#/accueil", None),
    ("2-chat-terre", "#/chat/" + urllib.parse.quote("J'ai une terre depuis 15 ans et j'ai appris qu'elle a un autre propriétaire. Que faire ?"), "haut"),
    ("3-chat-terre-suite", None, "bas"),          # même conversation, vue du bas (réponses rapides)
    ("4-chat-arabe", "#/chat/" + urllib.parse.quote("بابا سرقلي فلوسي شنعمل"), "haut"),
    ("5-lois", "#/lois", None),
    ("6-aide", "#/aide", None),
]


class Page:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=60, suppress_origin=True)
        self.n = 0

    def cmd(self, methode, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": methode, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == self.n:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m.get("result", {})

    def js(self, code):
        return self.cmd("Runtime.evaluate", expression=code, awaitPromise=True, returnByValue=True).get("result", {}).get("value")


def main():
    SORTIE.mkdir(parents=True, exist_ok=True)
    profil = tempfile.mkdtemp(prefix="amena-edge-")
    edge = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={profil}",
                             "--disable-gpu", "--hide-scrollbars", "--no-first-run", "about:blank"])
    try:
        for _ in range(50):
            try:
                cibles = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                cible = next(c for c in cibles if c.get("type") == "page")
                break
            except Exception:
                time.sleep(0.2)
        p = Page(cible["webSocketDebuggerUrl"])
        p.cmd("Page.enable")
        p.cmd("Emulation.setDeviceMetricsOverride", width=432, height=960, deviceScaleFactor=2.5, mobile=True)
        p.cmd("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
        for nom, ancre, vue in ECRANS:
            if ancre is not None:
                p.cmd("Page.navigate", url="about:blank")
                time.sleep(0.3)
                p.cmd("Page.navigate", url=BASE + ancre)
                time.sleep(3)
                if ancre.startswith("#/chat/"):
                    # attendre la fin de la réponse : les réponses rapides apparaissent à la toute fin
                    for _ in range(90):
                        if p.js("!!document.querySelector('.puces button') || !!document.querySelector('.msg-ia .sous')"):
                            break
                        time.sleep(1)
                    time.sleep(1)
            if vue == "haut":
                p.js("window.scrollTo(0, 0)")
            elif vue == "bas":
                p.js("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.8)
            image = p.cmd("Page.captureScreenshot", format="png")["data"]
            (SORTIE / f"{nom}.png").write_bytes(base64.b64decode(image))
            print("capture", nom)
    finally:
        edge.terminate()
        try:
            edge.wait(timeout=10)
        except Exception:
            edge.kill()
        shutil.rmtree(profil, ignore_errors=True)


if __name__ == "__main__":
    main()
