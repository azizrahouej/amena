"""Discuter avec AMENA dans le terminal (sans interface web).

Usage :  python scripts/discuter.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from amena.assistant import Assistant  # noqa: E402

if __name__ == "__main__":
    assistant = Assistant.charger()
    print(f"AMENA prête ({assistant.etat()}). Tapez 'q' pour quitter.\n")
    historique = []
    while True:
        message = input("Vous > ").strip()
        if message.lower() in {"q", "quit", "exit"}:
            break
        if not message:
            continue
        r = assistant.repondre(message, historique)
        print(f"\n[{r['triage']['label']} | {r['triage']['raison']} | {r['mode']} | {r['langue']}]")
        print(f"AMENA > {r['reponse']}\n")
        for s in r["sources"]:
            print(f"   source : {s['titre']} ({s['score']})")
        print()
        historique += [{"role": "user", "content": message},
                       {"role": "assistant", "content": r["reponse"]}]
