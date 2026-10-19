import pandas as pd

FICHIER = "resumeRoutingsAversB.csv"

COL_NOM = "Nom"
COL_DUREE = "Durée (brut)"
COL_VIREMENTS = "Nb de virements et empannages (brut)"
COL_MAX_BS = "Max BS (brut)"
COL_MIN_BS = "Min BS (brut)"

# Critères par ordre de priorité :
# (colonne, croissant ?, tolérance)
#   croissant = True  -> on cherche la plus petite valeur
#   croissant = False -> on cherche la plus grande valeur
#   tolérance : écart max (dans l'unité de la colonne) avec la meilleure valeur
#               pour qu'un parcours soit considéré "à égalité" sur ce critère
#               et passe donc au critère suivant.
# !!! Adapte les tolérances à l'unité réelle de tes colonnes "brut" !!!
CRITERES = [
    (COL_DUREE, True, 600),       # ex : 600 si la durée est en secondes (10 min)
    (COL_VIREMENTS, True, 2),     # 2 virements/empannages d'écart
    (COL_MAX_BS, False, 0.5),     # 0.5 nœud d'écart
    (COL_MIN_BS, False, 0.5),     # 0.5 nœud d'écart
]

# --- Lecture et mise en forme du tableau (visible dans Spyder) ---
df_complet = pd.read_csv(FICHIER, sep=";", encoding="utf-8-sig")

colonnes = [COL_NOM, COL_DUREE, COL_VIREMENTS, COL_MAX_BS, COL_MIN_BS]
tableau = df_complet[colonnes].copy()
for col in colonnes[1:]:
    tableau[col] = pd.to_numeric(
        tableau[col].astype(str).str.replace(",", ".", regex=False),
        errors="coerce",
    )
tableau = tableau.set_index(COL_NOM)


def meilleurs_candidats(candidats, criteres):
    """Garde, critère après critère, les parcours proches du meilleur
    (à la tolérance près). Retourne les candidats restants."""
    for colonne, croissant, tolerance in criteres:
        valeurs = candidats[colonne].dropna()
        if valeurs.empty:          # aucune valeur exploitable : on passe au critère suivant
            continue
        meilleure = valeurs.min() if croissant else valeurs.max()
        if croissant:
            candidats = candidats[candidats[colonne] <= meilleure + tolerance]
        else:
            candidats = candidats[candidats[colonne] >= meilleure - tolerance]
        if len(candidats) == 1:    # un seul survivant : inutile d'aller plus loin
            break
    return candidats


def classer(tableau, criteres):
    """Construit le classement complet : on extrait le meilleur parcours,
    puis on recommence sur les parcours restants."""
    restants = tableau.copy()
    ordre = []
    while not restants.empty:
        finalistes = meilleurs_candidats(restants, criteres)
        # s'il reste plusieurs finalistes après tous les critères, on prend
        # le premier critère (valeur exacte) pour les départager
        col0, croissant0, _ = criteres[0]
        gagnant = finalistes.sort_values(col0, ascending=croissant0, na_position="last").index[0]
        ordre.append(gagnant)
        restants = restants.drop(gagnant)
    return tableau.loc[ordre]


# --- Tris individuels (chacun est un tableau visible dans Spyder) ---
tri_duree = tableau.sort_values(COL_DUREE, ascending=True, na_position="last")
tri_virements = tableau.sort_values(COL_VIREMENTS, ascending=True, na_position="last")
tri_max_bs = tableau.sort_values(COL_MAX_BS, ascending=False, na_position="last")
tri_min_bs = tableau.sort_values(COL_MIN_BS, ascending=False, na_position="last")

# --- Classement avec tolérances et parcours optimal ---
classement = classer(tableau, CRITERES)
optimal = classement.index[0]

print("Classement (méthode avec tolérances) :")
print(classement)
print(f"\nParcours optimal : {optimal}")
