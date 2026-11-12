"""Lance qtVlm en mode batch : 1) routings, 2) export de la route choisie.

Utilisation :  python lancer_qtvlm.py
"""

import subprocess
import sys
import os
import re
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

""" # --- Mon PC -------------------------------------------------------------
QTVLM_EXE = r"C:\\Program Files\\qtVlm\\qtVlm.exe"
DOSSIER = Path(__file__).parent  # dossier des fichiers xml
BATCH_ROUTING = DOSSIER / "routing_4x4h.xml"
BATCH_EXPORT = DOSSIER / "export_route.xml"  # réécrit à chaque lancement
Directory_route = str(DOSSIER / "Sorties")  # dossier de sortie des fichiers exportés
PYTHON_VENV = DOSSIER / ".venv" / "Scripts" / "python.exe"
FORMAT_EXPORT = "csv"  # csv, gpx, kml ou json
# ---------------------------------------------------------------------------^ """

# --- PC HEAI-FR -------------------------------------------------------------
QTVLM_EXE = r"C:\Program Files\qtVlm\qtVlm.exe"
DOSSIER = Path(__file__).parent  # dossier des fichiers xml
BATCH_ROUTING = DOSSIER / "Routing.xml"
BATCH_EXPORT = DOSSIER / "export_route.xml"  # réécrit à chaque lancement
Directory_route = str(DOSSIER / "Sorties")  # dossier de sortie des fichiers exportés
PYTHON_VENV = DOSSIER / ".venv" / "Scripts" / "python.exe"
TELECHARGEUR_METEO = (
    DOSSIER
    / "GFS_NOAA_NOMADS_Downloader_for_XyGrib-72h_GRIB2_Forecast-main"
    / "xygrib-noaa.sh"
)

# Valeurs du batch de routage, modifiables selon le routage souhaité.
CLEAR_ALL_ROUTES = True
CLOSE_ALL_GRIBS = True
GRIB_SLOT_1 = DOSSIER / "Grib_Files" / "GFS_WW3_NOAA_20261019_00Z_72hs.grib2"
GRIB_SLOT_2 = ""
GRIB_SLOT_3 = ""
ROUTING_NAME = "routingAversB"
START_POINT = "A"
END_POINT = "B"
START_DATE = "10/20/2026" #Attention : la date doit être au format MM/DD/YYYY pour que qtVlm l'accepte correctement
START_TIME = "16:00:00"
NO_ROUTE_OUTSIDE_SCREEN = False
MULTI_ROUTING = True
GENERATE_ROUTES = 4
STEP_DAYS = 0
STEP_HOURS = 4
STEP_MINUTES = 0
AUTO_SIMP_OPTIM = True
COMPARATOR_CSV_FILE = DOSSIER / "Sorties" / "resumeRoutingsAversB.csv"
SCREENSHOT_FILE = DOSSIER / "Sorties" / "screenshot_routing.png"
QUIT_AFTER_ROUTING = True

# ---------------------------------------------------------------------------





####### Défnition des fonctions ########




# ---------------------- Fonctions pour vérifier et télécharger les données météo ----------------------

def obtenir_plage_meteo() -> tuple[datetime, datetime] | None:
    return obtenir_plage_fichier_meteo(GRIB_SLOT_1)


def obtenir_plage_fichier_meteo(fichier: Path) -> tuple[datetime, datetime] | None:
    correspondance = re.search(
        r"(?P<date>\d{8})(?:_(?P<cycle>\d{2})Z)?.*?(?P<heures>\d+)hs",
        fichier.name,
        re.IGNORECASE,
    )
    if correspondance is None:
        return None
    debut_meteo = datetime.strptime(
        f"{correspondance['date']}{correspondance['cycle'] or '00'}",
        "%Y%m%d%H",
    )
    fin_meteo = debut_meteo + timedelta(hours=int(correspondance["heures"]))
    return debut_meteo, fin_meteo


def trouver_grib_compatible() -> Path | None:
    global GRIB_SLOT_1

    try:
        debut_routage = datetime.strptime(
            f"{START_DATE} {START_TIME}", "%m/%d/%Y %H:%M:%S"
        )
        if GENERATE_ROUTES < 1 or STEP_DAYS < 0 or STEP_HOURS < 0 or STEP_MINUTES < 0:
            return None
        intervalle = timedelta(
            days=STEP_DAYS,
            hours=STEP_HOURS,
            minutes=STEP_MINUTES,
        )
        dernier_depart = debut_routage + (GENERATE_ROUTES - 1) * intervalle
    except ValueError:
        return None

    fichiers_compatibles: list[tuple[datetime, int, int, Path]] = []
    for fichier in GRIB_SLOT_1.parent.glob("GFS_*.grib2"):
        try:
            plage = obtenir_plage_fichier_meteo(fichier)
        except ValueError:
            continue
        if plage is None:
            continue
        debut_meteo, fin_meteo = plage
        if debut_meteo <= debut_routage and fin_meteo >= dernier_depart:
            correspondance = re.search(r"(\d+)hs", fichier.name, re.IGNORECASE)
            if correspondance is None:
                continue
            duree = int(correspondance.group(1))
            est_combine = int(fichier.name.startswith("GFS_WW3_"))
            fichiers_compatibles.append(
                (debut_meteo, duree, est_combine, fichier)
            )

    if not fichiers_compatibles:
        return None

    # Privilégie le cycle le plus récent, puis le forecast le plus court et le fichier combiné.
    fichier = max(
        fichiers_compatibles,
        key=lambda element: (element[0], -element[1], element[2]),
    )[3]
    GRIB_SLOT_1 = fichier
    print(f"Fichier météo correspondant trouvé : {GRIB_SLOT_1.name}")
    return fichier


def verifier_donnees_meteo() -> bool:
    if not GRIB_SLOT_1.is_file():
        print(f"Erreur : fichier GRIB2 introuvable : {GRIB_SLOT_1}")
        return False

    try:
        plage_meteo = obtenir_plage_meteo()
        if plage_meteo is None:
            print(
                "Erreur : le nom du fichier GRIB2 doit contenir une date AAAAMMJJ "
                "et une durée telle que 72hs."
            )
            return False
        debut_meteo, fin_meteo = plage_meteo
        debut_routage = datetime.strptime(
            f"{START_DATE} {START_TIME}", "%m/%d/%Y %H:%M:%S"
        )
    except ValueError as erreur:
        print(f"Erreur dans la date du GRIB ou du départ du routage : {erreur}")
        return False

    if GENERATE_ROUTES < 1 or STEP_DAYS < 0 or STEP_HOURS < 0 or STEP_MINUTES < 0:
        print("Erreur : le nombre de routes doit être positif et les pas non négatifs.")
        return False

    duree_pas = timedelta(
        days=STEP_DAYS,
        hours=STEP_HOURS,
        minutes=STEP_MINUTES,
    )
    dernier_depart = debut_routage + (GENERATE_ROUTES - 1) * duree_pas

    print(
        f"Données météo disponibles du {debut_meteo:%d/%m/%Y %H:%M} "
        f"au {fin_meteo:%d/%m/%Y %H:%M}."
    )
    if debut_routage < debut_meteo or debut_routage > fin_meteo:
        print(
            f"Erreur : le départ du routage ({debut_routage:%d/%m/%Y %H:%M}) "
            "est en dehors de la période météo."
        )
        return False
    if dernier_depart > fin_meteo:
        print(
            f"Erreur : le dernier départ planifié ({dernier_depart:%d/%m/%Y %H:%M}) "
            "est en dehors de la période météo."
        )
        return False

    print(
        f"Vérification météo OK : les {GENERATE_ROUTES} départs planifiés "
        f"restent dans les données (dernier départ : {dernier_depart:%d/%m/%Y %H:%M})."
    )
    return True


def trouver_bash() -> Path | None:
    bash = shutil.which("bash")
    if bash:
        return Path(bash)
    for chemin in (
        Path(r"C:\Program Files\Git\bin\bash.exe"),
        Path(r"C:\Program Files (x86)\Git\bin\bash.exe"),
    ):
        if chemin.is_file():
            return chemin
    return None


def chemin_git_bash(chemin: Path) -> str:
    chemin_windows = str(chemin.resolve())
    correspondance = re.match(r"^([A-Za-z]):\\(.*)$", chemin_windows)
    if correspondance is None:
        raise ValueError(f"Chemin Windows non pris en charge par Git Bash : {chemin}")
    return f"/{correspondance[1].lower()}/{correspondance[2].replace(chr(92), '/')}"


def demander_heures_prevision() -> int | None:
    while True:
        saisie = input("Durée des nouvelles données météo en heures (1 à 384) : ").strip()
        try:
            heures = int(saisie)
        except ValueError:
            print("Veuillez saisir un nombre entier d'heures.")
            continue
        if 1 <= heures <= 384:
            return heures
        print("La durée doit être comprise entre 1 et 384 heures.")


# --------------------- Téléchargement des données météo avec xygrib-noaa.sh ----------------------

def telecharger_donnees_meteo(heures: int) -> bool:
    global GRIB_SLOT_1

    bash = trouver_bash()
    if bash is None:
        print(
            "Erreur : Git Bash est introuvable. Installez Git for Windows "
            "pour exécuter le téléchargeur météo."
        )
        return False
    if not TELECHARGEUR_METEO.is_file():
        print(f"Erreur : téléchargeur météo introuvable : {TELECHARGEUR_METEO}")
        return False

    grib_dir = GRIB_SLOT_1.parent
    grib_dir.mkdir(parents=True, exist_ok=True)
    script_source = TELECHARGEUR_METEO.read_text(encoding="utf-8")
    script_source, nombre_horizons = re.subn(
        r"(?m)^MAX_FORECAST=\d+.*$",
        f"MAX_FORECAST={heures}  # configuré par Test_Commande.py",
        script_source,
    )
    if nombre_horizons != 1:
        print("Erreur : impossible de configurer MAX_FORECAST dans le téléchargeur.")
        return False

    with tempfile.TemporaryDirectory(
        prefix="qtvlm_grib_",
        dir=grib_dir,
    ) as dossier_temporaire:
        dossier_temp = Path(dossier_temporaire)
        dossier_sortie = dossier_temp / "grib"
        dossier_sortie.mkdir()
        script_source, nombre_dossiers = re.subn(
            r'(?m)^XYGRIB_DIR="[^"]*"$',
            f'XYGRIB_DIR="{chemin_git_bash(dossier_sortie)}"',
            script_source,
        )
        if nombre_dossiers != 1:
            print("Erreur : impossible de configurer le dossier de sortie du téléchargeur.")
            return False

        script_temporaire = dossier_temp / "xygrib-noaa.sh"
        script_temporaire.write_text(script_source, encoding="utf-8")
        print(f"Téléchargement des données météo ({heures} heures)...")
        resultat = subprocess.run(
            [str(bash), chemin_git_bash(script_temporaire)],
            cwd=TELECHARGEUR_METEO.parent,
            check=False,
        )
        if resultat.returncode != 0:
            print(f"Erreur : le téléchargement a échoué (code {resultat.returncode}).")
            return False

        fichiers_grib = list(dossier_sortie.glob("*.grib2"))
        if not fichiers_grib:
            print("Erreur : le téléchargement n'a produit aucun fichier GRIB2.")
            return False

        fichier_grib_gfs = next(
            (f for f in fichiers_grib if f.name.startswith("GFS_WW3_")),
            next((f for f in fichiers_grib if f.name.startswith("GFS_NOAA_")), None),
        )
        for fichier in fichiers_grib:
            destination = grib_dir / fichier.name
            os.replace(fichier, destination)
            print(f"Fichier météo enregistré : {destination}")

        if fichier_grib_gfs is None:
            print("Erreur : aucun fichier GRIB GFS exploitable n'a été téléchargé.")
            return False
        GRIB_SLOT_1 = grib_dir / fichier_grib_gfs.name
        print(f"Fichier météo utilisé : {GRIB_SLOT_1}")
        return True


#--------------------- Fonctions pour interagir avec l'utilisateur ----------------------
def demander_reponse_oui_non(question: str) -> bool:
    while True:
        reponse = input(f"{question} (oui/non) : ").strip().lower()
        if reponse in {"oui", "o"}:
            return True
        if reponse in {"non", "n"}:
            return False
        print("Répondez par oui ou non.")



#--------------------- Fonctions pour corriger la date de départ ----------------------
def demander_correction_date() -> bool:
    global START_DATE

    try:
        if not GRIB_SLOT_1.is_file():
            print("Impossible de proposer une date : le fichier GRIB2 est introuvable.")
            return False
        plage_meteo = obtenir_plage_meteo()
        if plage_meteo is None:
            print("Impossible de proposer une date : le nom du fichier météo est invalide.")
            return False
        debut_meteo, fin_meteo = plage_meteo
        duree_pas = timedelta(
            days=STEP_DAYS,
            hours=STEP_HOURS,
            minutes=STEP_MINUTES,
        )
        date_maximale = fin_meteo - (GENERATE_ROUTES - 1) * duree_pas
        heure_depart = datetime.strptime(START_TIME, "%H:%M:%S").time()
        date_min = debut_meteo.date()
        date_max = date_maximale.date()
        if datetime.combine(date_min, heure_depart) < debut_meteo:
            date_min += timedelta(days=1)
        if datetime.combine(date_max, heure_depart) > date_maximale:
            date_max -= timedelta(days=1)
        if date_min > date_max:
            print("Aucune date ne permet de faire tenir les départs dans ces données météo.")
            return False
        print(
            f"Plage possible pour START_DATE : {date_min:%m/%d/%Y} à "
            f"{date_max:%m/%d/%Y}, à l'heure {START_TIME}."
        )
    except (ValueError, OverflowError) as erreur:
        print(f"Impossible de calculer la plage des dates météo : {erreur}")
        return False

    while True:
        nouvelle_date = input("Nouvelle START_DATE (MM/DD/YYYY), ou Entrée pour annuler : ").strip()
        if not nouvelle_date:
            return False
        START_DATE = nouvelle_date
        if verifier_donnees_meteo():
            return True
        print("Cette date ne convient pas aux données météo disponibles. Réessayez.")


def preparer_donnees_meteo() -> bool:
    trouver_grib_compatible()
    if verifier_donnees_meteo():
        return True

    if demander_reponse_oui_non("Voulez-vous télécharger de nouvelles données météo ?"):
        heures = demander_heures_prevision()
        if heures is None or not telecharger_donnees_meteo(heures):
            return False
        if verifier_donnees_meteo():
            return True

    if demander_reponse_oui_non("Voulez-vous changer START_DATE selon la plage météo disponible ?"):
        return demander_correction_date()
    return False


def lancer_batch(fichier_xml: Path) -> int:
    """Lance qtVlm avec un fichier batch dans une console séparée et attend sa fin."""
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    proc = subprocess.Popen([QTVLM_EXE, str(fichier_xml)], creationflags=flags)
    return proc.wait()


def ecrire_batch_routing() -> None:
    xml = f"""<runs>
    <run>
        <clearAllRoutes>{str(CLEAR_ALL_ROUTES).lower()}</clearAllRoutes>
        <closeAllGribs>{str(CLOSE_ALL_GRIBS).lower()}</closeAllGribs>
        <gribSlot1>{escape(str(GRIB_SLOT_1))}</gribSlot1>
        <gribSlot2>{escape(str(GRIB_SLOT_2))}</gribSlot2>
        <gribSlot3>{escape(str(GRIB_SLOT_3))}</gribSlot3>
        <routingName>{escape(ROUTING_NAME)}</routingName>
        <startPoint>{escape(START_POINT)}</startPoint>
        <endPoint>{escape(END_POINT)}</endPoint>
        <startDate>{escape(START_DATE)}</startDate>
        <startTime>{escape(START_TIME)}</startTime>
        <noRouteOutsideScreen>{str(NO_ROUTE_OUTSIDE_SCREEN).lower()}</noRouteOutsideScreen>
        <multiRouting>{str(MULTI_ROUTING).lower()}</multiRouting>
        <generateRoutes>{GENERATE_ROUTES}</generateRoutes>
        <stepDays>{STEP_DAYS}</stepDays>
        <stepHours>{STEP_HOURS}</stepHours>
        <stepMins>{STEP_MINUTES}</stepMins>
        <autoSimpOptim>{str(AUTO_SIMP_OPTIM).lower()}</autoSimpOptim>
        <comparatorCsvFile>{escape(str(COMPARATOR_CSV_FILE))}</comparatorCsvFile>
        
    </run>
    <run>
        <quit>{str(QUIT_AFTER_ROUTING).lower()}</quit>
    </run>
</runs>
"""
    BATCH_ROUTING.write_text(xml, encoding="utf-8")

#<takeScreenShot>{escape(str(SCREENSHOT_FILE))}</takeScreenShot>

def ecrire_batch_export(directory_route: str) -> None: # écrit le fichier export_route.xml pour exporter la route choisie
    xml = f"""<runs>
        <run>
            <exportFolder>{directory_route}</exportFolder>
            <exportRoutesLogs>true</exportRoutesLogs>
        </run>
        <run>
            <quit>true</quit>
        </run>
    </runs>
"""

    BATCH_EXPORT.write_text(xml, encoding="utf-8") #ecriture du fichier utilisable par qtVlm pour l'export de la route choisie



def main() -> None:
    if not preparer_donnees_meteo():
        sys.exit("Données météo insuffisantes ; opération annulée.")

    os.makedirs(Directory_route, exist_ok=True)  # crée le dossier s'il manque

    if not Path(QTVLM_EXE).exists():
        sys.exit(f"qtVlm introuvable : {QTVLM_EXE}") # dit que qtVlm n'est pas trouvé si le chemin est incorrect
    if not PYTHON_VENV.is_file():
        sys.exit(f"Interpréteur du projet introuvable : {PYTHON_VENV}")

    ecrire_batch_routing()
    print("1) Lancement des routings...") #Première étape : lancement des routings
    code = lancer_batch(BATCH_ROUTING)
    print(f"   qtVlm fermé (code de sortie {code}).")
    if code != 0:
        print("   Attention : code 1 = une commande du batch a échoué, voir le log.")

    print("2) Export de la route...") #Deuxième étape : export de la route choisie
    ecrire_batch_export(Directory_route)
    code = lancer_batch(BATCH_EXPORT)
    print(f"   Terminé (code de sortie {code}). Fichier dans : {Directory_route}")

    print("3) Analyse des routings...") #Troisième étape : analyse des routings avec le script analyse_routings_ponderation.py
    resultat = subprocess.run(
        [str(PYTHON_VENV), str(DOSSIER / "analyse_routings_ponderation.py")],
        cwd=DOSSIER,
        capture_output=True,
        text=True,
        check=False,
    )
    print(resultat.stdout, end="")
    if resultat.stderr:
        print(resultat.stderr, file=sys.stderr, end="")
    if resultat.returncode != 0:
        sys.exit(f"Échec de l'analyse des routings (code {resultat.returncode}).")



############## Main ##############

if __name__ == "__main__":
    main()
