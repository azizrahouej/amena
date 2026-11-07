"""Données externes : Banque mondiale, « Women, Business and the Law 2026 » (WBL 2.0).

Source  : https://datacatalog.worldbank.org/search/dataset/0038489/women-business-and-the-law
Fichier : 2026.02.19_WBL26_FINAL_Data_for_Download.xlsx (feuille « 1. Safety »)
Licence : Creative Commons Attribution 4.0 — citation : World Bank. 2026. Women, Business and
          the Law 2026. Washington, DC: World Bank.

Pour 190 pays, la feuille « Safety » indique si la loi traite le mariage des enfants, le
harcèlement sexuel, la violence domestique et le féminicide, avec la BASE LÉGALE précise (article
de loi), ainsi que les dispositifs d'aide (plan d'action, unités spécialisées, refuges...) et la
perception de l'application réelle des lois.

Nettoyage (même démarche que la séance « Préparer un fichier CSV ») :
    1. reconstruire les en-têtes (le fichier a 3 lignes d'en-tête : titre, code, libellé) ;
    2. supprimer les colonnes dupliquées (les trois scores de thème apparaissent deux fois) ;
    3. typer : « Yes »/« No » -> booléens, scores -> nombres entre 0 et 100 ; une case vide
       signifie « non applicable » et n'est PAS convertie en « non » ; le score d'application
       manquant (13 pays non enquêtés) n'est pas imputé ;
    4. les sources « No applicable provisions could be located » et « Insufficient evidence
       located » ne sont pas des sources : elles deviennent des valeurs manquantes ;
    5. normaliser le texte (apostrophes typographiques, espaces insécables) ;
    6. vérifier : unicité des pays, bornes des scores, cohérence réponse / base légale ;
    7. passer au format long : une ligne par pays et par question ;
    8. traduire en français les questions et les noms de pays.
"""

import re
import unicodedata

import pandas as pd

from .config import RACINE

DOSSIER_WBL = RACINE / "data" / "wbl"
FICHIER_PAYS = DOSSIER_WBL / "wbl2026_pays.csv"
FICHIER_INDICATEURS = DOSSIER_WBL / "wbl2026_indicateurs.csv"
FICHIER_BRUT = RACINE / "data" / "externe" / "wbl2026" / "WBL2026_2-0.xlsx"
CITATION = "Banque mondiale, Women, Business and the Law 2026 (CC BY 4.0)"

ABSENCES = {"no applicable provisions could be located", "insufficient evidence located", "n/a", "nan", ""}

# Scores agrégés conservés pour chaque pays (0 à 100).
SCORES = {
    "Saf_Law_ts": "score_cadre_legal",
    "Saf_SFR_ts": "score_dispositifs",
    "Saf_Enf_ts": "score_application",
    "Saf_Law_ChildMarr_is": "sous_mariage_enfants",
    "Saf_Law_SexHarass_is": "sous_harcelement",
    "Saf_Law_DomViol_is": "sous_violence_domestique",
    "Saf_Law_Femicide_is": "sous_feminicide",
}

# Questions oui / non : code WBL -> (pilier, thème, libellé français).
QUESTIONS = {
    "Saf_Law_ChildMarr_Age": ("cadre_legal", "Mariage des enfants", "L'âge légal du mariage est-il d'au moins 18 ans pour les filles et les garçons ?"),
    "Saf_Law_ChildMarr_ParEx18": ("cadre_legal", "Mariage des enfants", "La loi exclut-elle toute exception à l'âge légal par consentement parental ?"),
    "Saf_Law_ChildMarr_Void": ("cadre_legal", "Mariage des enfants", "Un mariage avant l'âge légal est-il nul ou annulable ?"),
    "Saf_Law_ChildMarr_Penalty": ("cadre_legal", "Mariage des enfants", "Des sanctions visent-elles les adultes qui autorisent ou célèbrent un mariage d'enfant ?"),
    "Saf_Law_SexHar_EplCpCr": ("cadre_legal", "Harcèlement sexuel", "Le harcèlement sexuel au travail est-il sanctionné ?"),
    "Saf_Law_SexHar_EduCpCr": ("cadre_legal", "Harcèlement sexuel", "Le harcèlement sexuel dans l'éducation est-il sanctionné ?"),
    "Saf_Law_SexHar_PubCpCr": ("cadre_legal", "Harcèlement sexuel", "Le harcèlement sexuel dans l'espace public ou les transports est-il sanctionné ?"),
    "Saf_Law_SexHar_CybCpCr": ("cadre_legal", "Harcèlement sexuel", "Le cyber-harcèlement est-il sanctionné ?"),
    "Saf_Law_DomViolLaw": ("cadre_legal", "Violence domestique", "Existe-t-il une loi ou une disposition sur la violence domestique ?"),
    "Saf_Law_DomViol_CrimPen": ("cadre_legal", "Violence domestique", "Cette législation prévoit-elle des sanctions pénales ?"),
    "Saf_Law_DomViol_ProtOrd": ("cadre_legal", "Violence domestique", "Prévoit-elle des ordonnances de protection ?"),
    "Saf_Law_DomViol_Physical": ("cadre_legal", "Violence domestique", "Couvre-t-elle la violence physique ?"),
    "Saf_Law_DomViol_Psychol": ("cadre_legal", "Violence domestique", "Couvre-t-elle la violence psychologique ?"),
    "Saf_Law_DomViol_EcoFin": ("cadre_legal", "Violence domestique", "Couvre-t-elle la violence économique ?"),
    "Saf_Law_DomViol_SexualMR": ("cadre_legal", "Violence domestique", "Couvre-t-elle la violence sexuelle, y compris le viol conjugal ?"),
    "Saf_Law_FemicideCr": ("cadre_legal", "Féminicide", "Le féminicide est-il une infraction spécifique ?"),
    "Saf_Law_FemicideAP": ("cadre_legal", "Féminicide", "Le meurtre d'une femme est-il puni de peines aggravées ?"),
    "Saf_SFR_ActPln_Prev": ("dispositifs", "Plan d'action", "Le plan national contre la violence prévoit-il des mesures de prévention ?"),
    "Saf_SFR_ActPln_Inst": ("dispositifs", "Plan d'action", "Le plan désigne-t-il les institutions responsables ?"),
    "Saf_SFR_ActPln_Targets": ("dispositifs", "Plan d'action", "Le plan fixe-t-il des objectifs et des indicateurs ?"),
    "Saf_SFR_AJustice_PolProsc": ("dispositifs", "Accès à la justice", "Existe-t-il des unités de police ou de parquet spécialisées ?"),
    "Saf_SFR_AJustice_Courts": ("dispositifs", "Accès à la justice", "Existe-t-il des tribunaux ou procédures spécialisés ?"),
    "Saf_SFR_AJustice_LegalAid": ("dispositifs", "Accès à la justice", "Une aide juridique est-elle offerte aux victimes ?"),
    "Saf_SFR_Services_Shelter": ("dispositifs", "Services aux victimes", "Existe-t-il des refuges pour les femmes victimes ?"),
    "Saf_SFR_Services_Health": ("dispositifs", "Services aux victimes", "Existe-t-il des services de santé dédiés ?"),
    "Saf_SFR_Services_Psychol": ("dispositifs", "Services aux victimes", "Existe-t-il un soutien psychologique ?"),
    "Saf_SFR_Services_LivHood": ("dispositifs", "Services aux victimes", "Existe-t-il une aide à l'autonomie économique ?"),
}

# Noms français (les noms anglais servent de repli). Codes ISO 3166-1 alpha-3.
NOMS_FR = {
    "AFG": "Afghanistan", "ALB": "Albanie", "DZA": "Algérie", "AGO": "Angola", "ARG": "Argentine", "ARM": "Arménie",
    "AUS": "Australie", "AUT": "Autriche", "AZE": "Azerbaïdjan", "BHR": "Bahreïn", "BGD": "Bangladesh", "BEL": "Belgique",
    "BEN": "Bénin", "BOL": "Bolivie", "BIH": "Bosnie-Herzégovine", "BWA": "Botswana", "BRA": "Brésil", "BGR": "Bulgarie",
    "BFA": "Burkina Faso", "BDI": "Burundi", "KHM": "Cambodge", "CMR": "Cameroun", "CAN": "Canada", "CPV": "Cap-Vert",
    "CAF": "République centrafricaine", "TCD": "Tchad", "CHL": "Chili", "CHN": "Chine", "COL": "Colombie", "COM": "Comores",
    "COD": "République démocratique du Congo", "COG": "République du Congo", "CRI": "Costa Rica", "CIV": "Côte d'Ivoire",
    "HRV": "Croatie", "CYP": "Chypre", "CZE": "Tchéquie", "DNK": "Danemark", "DJI": "Djibouti", "DOM": "République dominicaine",
    "ECU": "Équateur", "EGY": "Égypte", "SLV": "Salvador", "GNQ": "Guinée équatoriale", "ERI": "Érythrée", "EST": "Estonie",
    "SWZ": "Eswatini", "ETH": "Éthiopie", "FIN": "Finlande", "FRA": "France", "GAB": "Gabon", "GMB": "Gambie", "GEO": "Géorgie",
    "DEU": "Allemagne", "GHA": "Ghana", "GRC": "Grèce", "GTM": "Guatemala", "GIN": "Guinée", "GNB": "Guinée-Bissau",
    "HTI": "Haïti", "HND": "Honduras", "HUN": "Hongrie", "ISL": "Islande", "IND": "Inde", "IDN": "Indonésie", "IRN": "Iran",
    "IRQ": "Irak", "IRL": "Irlande", "ISR": "Israël", "ITA": "Italie", "JAM": "Jamaïque", "JPN": "Japon", "JOR": "Jordanie",
    "KAZ": "Kazakhstan", "KEN": "Kenya", "KOR": "Corée du Sud", "KWT": "Koweït", "KGZ": "Kirghizistan", "LAO": "Laos",
    "LVA": "Lettonie", "LBN": "Liban", "LSO": "Lesotho", "LBR": "Liberia", "LBY": "Libye", "LTU": "Lituanie",
    "LUX": "Luxembourg", "MDG": "Madagascar", "MWI": "Malawi", "MYS": "Malaisie", "MDV": "Maldives", "MLI": "Mali",
    "MLT": "Malte", "MRT": "Mauritanie", "MUS": "Maurice", "MEX": "Mexique", "MDA": "Moldavie", "MNG": "Mongolie",
    "MNE": "Monténégro", "MAR": "Maroc", "MOZ": "Mozambique", "MMR": "Myanmar", "NAM": "Namibie", "NPL": "Népal",
    "NLD": "Pays-Bas", "NZL": "Nouvelle-Zélande", "NIC": "Nicaragua", "NER": "Niger", "NGA": "Nigeria", "MKD": "Macédoine du Nord",
    "NOR": "Norvège", "OMN": "Oman", "PAK": "Pakistan", "PAN": "Panama", "PRY": "Paraguay", "PER": "Pérou",
    "PHL": "Philippines", "POL": "Pologne", "PRT": "Portugal", "QAT": "Qatar", "ROU": "Roumanie", "RUS": "Russie",
    "RWA": "Rwanda", "SAU": "Arabie saoudite", "SEN": "Sénégal", "SRB": "Serbie", "SLE": "Sierra Leone", "SGP": "Singapour",
    "SVK": "Slovaquie", "SVN": "Slovénie", "SOM": "Somalie", "ZAF": "Afrique du Sud", "SSD": "Soudan du Sud", "ESP": "Espagne",
    "LKA": "Sri Lanka", "SDN": "Soudan", "SWE": "Suède", "CHE": "Suisse", "SYR": "Syrie", "TJK": "Tadjikistan",
    "TZA": "Tanzanie", "THA": "Thaïlande", "TGO": "Togo", "TUN": "Tunisie", "TUR": "Turquie", "UGA": "Ouganda",
    "UKR": "Ukraine", "ARE": "Émirats arabes unis", "GBR": "Royaume-Uni", "USA": "États-Unis", "URY": "Uruguay",
    "UZB": "Ouzbékistan", "VEN": "Venezuela", "VNM": "Viêt Nam", "PSE": "Cisjordanie et Gaza", "YEM": "Yémen",
    "ZMB": "Zambie", "ZWE": "Zimbabwe", "BLR": "Biélorussie", "SUR": "Suriname", "GUY": "Guyana", "BLZ": "Belize",
    "BTN": "Bhoutan", "BRN": "Brunei", "TLS": "Timor oriental", "PNG": "Papouasie-Nouvelle-Guinée", "FJI": "Fidji",
    "STP": "Sao Tomé-et-Principe", "SYC": "Seychelles", "XKX": "Kosovo", "HKG": "Hong Kong (Chine)", "TWN": "Taïwan (Chine)",
    "ATG": "Antigua-et-Barbuda", "BHS": "Bahamas", "BRB": "Barbade", "DMA": "Dominique", "GRD": "Grenade",
    "KIR": "Kiribati", "MHL": "Îles Marshall", "FSM": "Micronésie", "PLW": "Palaos", "PRI": "Porto Rico",
    "WSM": "Samoa", "SMR": "Saint-Marin", "SLB": "Îles Salomon", "KNA": "Saint-Christophe-et-Niévès",
    "LCA": "Sainte-Lucie", "VCT": "Saint-Vincent-et-les-Grenadines", "TTO": "Trinité-et-Tobago", "TON": "Tonga",
    "VUT": "Vanuatu", "PRY": "Paraguay", "URY": "Uruguay", "KOS": "Kosovo",
}
REGIONS_FR = {
    "East Asia & Pacific": "Asie de l'Est et Pacifique", "Europe & Central Asia": "Europe et Asie centrale",
    "Latin America & Caribbean": "Amérique latine et Caraïbes", "Middle East & North Africa": "Moyen-Orient et Afrique du Nord",
    "North America": "Amérique du Nord", "South Asia": "Asie du Sud", "Sub-Saharan Africa": "Afrique subsaharienne",
    "High income: OECD": "Revenu élevé : OCDE",
}
REVENUS_FR = {
    "Low income": "Revenu faible", "Lower middle income": "Revenu intermédiaire (tranche inférieure)",
    "Upper middle income": "Revenu intermédiaire (tranche supérieure)", "High income": "Revenu élevé",
}
# Codes de la bibliothèque juridique (ISO alpha-2) -> codes WBL (alpha-3).
ISO2_VERS_ISO3 = {"TN": "TUN", "MA": "MAR", "DZ": "DZA", "FR": "FRA", "ES": "ESP", "LB": "LBN"}


def normaliser_texte(valeur):
    """Apostrophes typographiques, espaces insécables, espaces multiples."""
    if pd.isna(valeur):
        return None
    texte = unicodedata.normalize("NFC", str(valeur))
    texte = texte.replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    texte = re.sub(r"\s+", " ", texte).strip()
    return None if texte.lower() in ABSENCES else texte


def lire_feuille_securite(fichier=FICHIER_BRUT):
    """Lit la feuille « 1. Safety » et reconstruit des en-têtes exploitables (étapes 1 et 2)."""
    brut = pd.read_excel(fichier, sheet_name="1. Safety", header=None)
    codes, libelles = brut.iloc[1], brut.iloc[2]
    # Les 6 premières colonnes n'ont pas de code : on les nomme à partir de leur libellé.
    noms = [codes[i] if pd.notna(codes[i]) else str(libelles[i]) for i in range(brut.shape[1])]
    donnees = brut.iloc[3:].reset_index(drop=True)
    donnees.columns = noms
    # Colonnes dupliquées : les scores de thème sont recopiés en tête de bloc ; on garde la première.
    donnees = donnees.loc[:, ~donnees.columns.duplicated()]
    return donnees, dict(zip(noms, libelles))


def nettoyer(fichier=FICHIER_BRUT):
    """Renvoie (pays, indicateurs) : deux tableaux propres, prêts à charger en base."""
    df, libelles = lire_feuille_securite(fichier)
    # « Economy Code » suit la codification interne de la Banque mondiale (ZAR, ROM, WBG...) ;
    # « ISO Code » suit la norme ISO 3166, celle qu'on utilise partout ailleurs.
    df = df.rename(columns={"Economy": "pays_en", "ISO Code": "iso3", "Economy Code": "code_bm",
                            "Region": "region_en", "Income Group": "revenu", "Report Year": "annee"})
    df["iso3"] = df["iso3"].astype(str).str.strip().str.upper()

    pays = df[["iso3", "pays_en", "region_en", "revenu", "annee"]].copy()
    pays["pays_fr"] = pays["iso3"].map(NOMS_FR).fillna(pays["pays_en"])
    pays["region_fr"] = pays["region_en"].map(REGIONS_FR).fillna(pays["region_en"])
    pays["revenu"] = pays["revenu"].map(REVENUS_FR).fillna(pays["revenu"])
    pays["annee"] = pd.to_numeric(pays["annee"], errors="coerce").astype("Int64")
    for code, nom in SCORES.items():
        valeurs = pd.to_numeric(df[code], errors="coerce")
        # Les sous-scores (« _is ») vont de 0 à 1 dans le fichier : on les ramène sur 100.
        pays[nom] = (valeurs * 100 if code.endswith("_is") else valeurs).round(2)

    lignes = []
    for code, (pilier, theme, question_fr) in QUESTIONS.items():
        colonne_base = f"{code}_LB"
        for _, ligne in df.iterrows():
            valeur = ligne[code]
            reponse = None if pd.isna(valeur) else str(valeur).strip().lower()
            if reponse not in (None, "yes", "no"):
                raise ValueError(f"Réponse inattendue {valeur!r} pour {code} ({ligne['iso3']})")
            lignes.append({
                "iso3": ligne["iso3"], "code": code, "pilier": pilier, "theme": theme,
                "question_fr": question_fr, "question_en": normaliser_texte(libelles.get(code)),
                # Une case vide signifie « non applicable » : par exemple, les sous-questions du plan
                # d'action quand le pays n'en a pas. On ne la transforme PAS en « non ».
                "reponse": {"yes": True, "no": False}.get(reponse),
                "base_legale": normaliser_texte(ligne.get(colonne_base)),
            })
    indicateurs = pd.DataFrame(lignes)
    return pays.sort_values("pays_fr").reset_index(drop=True), indicateurs


def verifier(pays, indicateurs):
    """Contrôles qualité : lève une erreur si une règle est violée (étape 6)."""
    erreurs = []
    if pays["iso3"].duplicated().any():
        erreurs.append("codes pays en double")
    for colonne in SCORES.values():
        hors = pays[(pays[colonne] < 0) | (pays[colonne] > 100)]
        if len(hors):
            erreurs.append(f"{colonne} hors de [0, 100] pour {len(hors)} pays")
    if indicateurs.duplicated(subset=["iso3", "code"]).any():
        erreurs.append("couples pays/question en double")
    if erreurs:
        raise ValueError(" ; ".join(erreurs))
    oui = indicateurs["reponse"] == True  # noqa: E712 (les valeurs manquantes restent exclues)
    return {
        "pays": len(pays),
        "indicateurs": len(indicateurs),
        "reponses_oui": int(oui.sum()),
        "reponses_non": int((indicateurs["reponse"] == False).sum()),  # noqa: E712
        "non_applicables": int(indicateurs["reponse"].isna().sum()),
        "bases_legales_citees": int(indicateurs["base_legale"].notna().sum()),
        # Une réponse « oui » sans base légale serait suspecte : on la compte pour information.
        "oui_sans_base": int((oui & indicateurs["base_legale"].isna()).sum()),
    }


def sauvegarder(pays, indicateurs):
    DOSSIER_WBL.mkdir(parents=True, exist_ok=True)
    pays.to_csv(FICHIER_PAYS, index=False, encoding="utf-8-sig")
    indicateurs.to_csv(FICHIER_INDICATEURS, index=False, encoding="utf-8-sig")


def charger_en_base(cnx):
    """Charge les CSV propres dans SQLite (tables monde_pays, monde_indicateurs)."""
    if not FICHIER_PAYS.exists():
        if not FICHIER_BRUT.exists():
            return {"pays": 0, "indicateurs": 0}
        sauvegarder(*nettoyer())
    pays = pd.read_csv(FICHIER_PAYS, encoding="utf-8-sig")
    indicateurs = pd.read_csv(FICHIER_INDICATEURS, encoding="utf-8-sig")
    with cnx:
        cnx.execute("DELETE FROM monde_indicateurs")
        cnx.execute("DELETE FROM monde_pays")
        colonnes = ["iso3", "pays_fr", "pays_en", "region_fr", "revenu", "annee", *SCORES.values()]
        cnx.executemany(f"INSERT INTO monde_pays ({', '.join(colonnes)}) VALUES ({', '.join('?' * len(colonnes))})",
                        pays[colonnes].astype(object).where(pays[colonnes].notna(), None).values.tolist())
        cnx.executemany("""INSERT INTO monde_indicateurs (iso3, code, pilier, theme, question, reponse, base_legale)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        [(r.iso3, r.code, r.pilier, r.theme, r.question_fr,
                          None if pd.isna(r.reponse) else int(bool(r.reponse)),
                          r.base_legale if isinstance(r.base_legale, str) else None)
                         for r in indicateurs.itertuples()])
    return {"pays": len(pays), "indicateurs": len(indicateurs)}


if __name__ == "__main__":
    p, i = nettoyer()
    print(verifier(p, i))
    sauvegarder(p, i)
    print(f"Écrit : {FICHIER_PAYS} et {FICHIER_INDICATEURS}")
