import pandas as pd

FICHIER = "resumeRoutingsAversB.csv"

COL_NOM = "Nom"
COL_DUREE = "Durée (brut)"
COL_VIREMENTS = "Nb de virements et empannages (brut)"
COL_MAX_BS = "Max BS (brut)"
COL_MIN_BS = "Min BS (brut)"

# Critères : colonne -> (croissant ?, poids)
#   croissant = True  -> plus petit = meilleur (durée, virements)
#   croissant = False -> plus grand = meilleur (vitesses)
#   poids : importance relative du critère (seuls les rapports comptent)
CRITERES = {
    COL_DUREE: (True, 4),
    COL_VIREMENTS: (True, 2),
    COL_MAX_BS: (False, 1),
    COL_MIN_BS: (False, 1),
}

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


def normaliser(serie, croissant):
    """Ramène une colonne entre 0 (pire) et 1 (meilleur).
    Valeur manquante -> 0. Si tous les parcours sont égaux -> 1."""
    mini, maxi = serie.min(), serie.max()
    if pd.isna(mini) or maxi == mini:
        score = pd.Series(1.0, index=serie.index)
    elif croissant:
        score = (maxi - serie) / (maxi - mini)
    else:
        score = (serie - mini) / (maxi - mini)
    return score.fillna(0.0)


# --- Scores normalisés par critère (colonnes "score_...") ---
scores = pd.DataFrame(index=tableau.index)
for colonne, (croissant, _) in CRITERES.items():
    scores["score_" + colonne] = normaliser(tableau[colonne], croissant)

# --- Score global pondéré (entre 0 et 1) ---
somme_poids = sum(poids for _, poids in CRITERES.values())
score_global = (
    sum(scores["score_" + colonne] * poids for colonne, (_, poids) in CRITERES.items())
    / somme_poids
)

# --- Tableau final : données + scores + score global, trié ---
resultat = tableau.join(scores)
resultat["score_global"] = score_global
classement = resultat.sort_values("score_global", ascending=False)

# --- Tris individuels (chacun est un tableau visible dans Spyder) ---
tri_duree = tableau.sort_values(COL_DUREE, ascending=True, na_position="last")
tri_virements = tableau.sort_values(COL_VIREMENTS, ascending=True, na_position="last")
tri_max_bs = tableau.sort_values(COL_MAX_BS, ascending=False, na_position="last")
tri_min_bs = tableau.sort_values(COL_MIN_BS, ascending=False, na_position="last")

# --- Parcours optimal ---
optimal = classement.index[0]

print("Classement (méthode avec pondération) :")
print(classement[["score_global"]])
print(f"\nParcours optimal : {optimal}")
