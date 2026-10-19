import pandas as pd

FICHIER = "resumeRoutingsAversB.csv"

# Colonnes utilisées (valeurs "brut", numériques)
COL_NOM = "Nom"
COL_DUREE = "Durée (brut)"
COL_VIREMENTS = "Nb de virements et empannages (brut)"
COL_MAX_BS = "Max BS (brut)"
COL_MIN_BS = "Min BS (brut)"

# Critères du classement combiné, par ordre de priorité :
# (colonne, croissant ?)  -> True = plus petit d'abord, False = plus grand d'abord
# Modifie cette liste pour changer la définition du parcours "optimal".
CRITERES = [
    (COL_DUREE, True),       # durée la plus courte
    (COL_VIREMENTS, True),   # le moins de virements/empannages
    (COL_MAX_BS, False),     # vitesse max la plus élevée
    (COL_MIN_BS, False),     # vitesse min la plus élevée
]

# --- Lecture du fichier complet (visible dans Spyder : variable "df_complet") ---
df_complet = pd.read_csv(FICHIER, sep=";", encoding="utf-8-sig")

# --- Tableau réduit aux colonnes utiles (variable "tableau") ---
colonnes = [COL_NOM, COL_DUREE, COL_VIREMENTS, COL_MAX_BS, COL_MIN_BS]
tableau = df_complet[colonnes].copy()
for col in colonnes[1:]:
    # convertit en nombre (gère la virgule décimale), valeur illisible -> NaN
    tableau[col] = pd.to_numeric(
        tableau[col].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
tableau = tableau.set_index(COL_NOM)

# --- Tris individuels (chacun est un tableau visible dans Spyder) ---
tri_duree = tableau.sort_values(COL_DUREE, ascending=True, na_position="last")
tri_virements = tableau.sort_values(COL_VIREMENTS, ascending=True, na_position="last")
tri_max_bs = tableau.sort_values(COL_MAX_BS, ascending=False, na_position="last")
tri_min_bs = tableau.sort_values(COL_MIN_BS, ascending=False, na_position="last")

# --- Classement combiné ---
classement = tableau.sort_values(
    by=[c for c, _ in CRITERES],
    ascending=[a for _, a in CRITERES],
    na_position="last",
)

# --- Parcours optimal : nom en haut du classement ---
optimal = classement.index[0]

print("Classement combiné :")
print(classement)
print(f"\nParcours optimal : {optimal}")