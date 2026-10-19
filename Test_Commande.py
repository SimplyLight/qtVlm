"""Lance qtVlm en mode batch : 1) routings, 2) export de la route choisie.

Utilisation :  python lancer_qtvlm.py
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

# --- À adapter -------------------------------------------------------------
DOSSIER_QTVLM = Path(r"C:\Program Files\qtVlm")
QTVLM_EXE = r"C:/Program Files/qtVlm/qtVlm.exe"
DOSSIER = Path(__file__).parent  # dossier des fichiers xml
BATCH_ROUTING = DOSSIER / "routing_4x4h.xml"
BATCH_EXPORT = DOSSIER / "export_route.xml"  # réécrit à chaque lancement
DOSSIER_EXPORT = str(DOSSIER / "Sorties")  # dossier de sortie des fichiers exportés
FORMAT_EXPORT = "csv"  # csv, gpx, kml ou json
NOM_ROUTE = "routingAversB_001 09 oct.-14:00"  # input("\nNom exact de la route à exporter : ").strip()
NOM_FICHIER_EXPORT = "routingAversB_001_09_oct.-14_00.csv"  # Nom du fichier exporté telle que créé par qtVlm, à copier dans le dossier d'export.
# ---------------------------------------------------------------------------


def lancer_batch(fichier_xml: Path) -> int:
    """Lance qtVlm avec un fichier batch dans une console séparée et attend sa fin."""
    flags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    proc = subprocess.Popen([QTVLM_EXE, str(fichier_xml)], creationflags=flags)
    return proc.wait()


def ecrire_batch_export(nom_route: str) -> None:
    xml = f"""<runs>
	<run>
		<exportFolder>{DOSSIER_EXPORT}</exportFolder>
	</run>
	<run>
		<exportRoute>{nom_route}</exportRoute>
		<exportFormat>{FORMAT_EXPORT}</exportFormat>
	</run>
	<run>
		<quit>true</quit>
	</run>
</runs>
"""
    BATCH_EXPORT.write_text(xml, encoding="utf-8")


def diagnostic() -> None:
    print("=== DIAGNOSTIC ===")
    print("Script file       :", Path(__file__).resolve())
    print("Working directory :", Path.cwd())
    for label, p in [
        ("qtVlm.exe", QTVLM_EXE),
        ("Routing batch", BATCH_ROUTING),
        ("Export batch", BATCH_EXPORT),
        ("Export folder", DOSSIER_EXPORT),
    ]:
        p = Path(p)
        print(f"{label:18}: {p} -> {'FOUND' if p.exists() else 'NOT FOUND'}")
    print("==================\n")


def transferer_export() -> None:
    source = DOSSIER_QTVLM / NOM_FICHIER_EXPORT
    destination = Path(DOSSIER_EXPORT) / NOM_FICHIER_EXPORT
    Path(DOSSIER_EXPORT).mkdir(parents=True, exist_ok=True)

    if not source.exists():
        print(f"   Fichier introuvable : {source}")
        return
    try:
        shutil.move(str(source), str(destination))
        print(f"   Fichier déplacé vers : {destination}")
    except PermissionError:
        # Program Files peut interdire la suppression : on copie au moins le fichier
        shutil.copy2(str(source), str(destination))
        print(
            f"   Fichier copié (original non supprimé, droits insuffisants) : {destination}"
        )


def main() -> None:
    # diagnostic()
    os.makedirs(DOSSIER_EXPORT, exist_ok=True)  # crée le dossier s'il manque

    if not Path(QTVLM_EXE).exists():
        sys.exit(f"qtVlm introuvable : {QTVLM_EXE}")

    print("1) Lancement des routings...")
    code = lancer_batch(BATCH_ROUTING)
    print(f"   qtVlm fermé (code de sortie {code}).")
    if code != 0:
        print("   Attention : code 1 = une commande du batch a échoué, voir le log.")

    nom = NOM_ROUTE
    if not nom:
        sys.exit("Aucun nom saisi, export annulé.")

    print("2) Export de la route...")
    ecrire_batch_export(nom)
    code = lancer_batch(BATCH_EXPORT)
    print(f"   Terminé (code de sortie {code}). Fichier dans : {DOSSIER_EXPORT}")

    print("\nFiles in the export folder:")
    for f in sorted(Path(DOSSIER_EXPORT).glob("*")):
        print("  ", f.name)

    transferer_export()
    print(f"   Terminé (code de sortie {code}).")


if __name__ == "__main__":
    main()
