"""Chemins des piles et paramètres communs des expériences de débruitage."""
from pathlib import Path

# --- Chemins des piles et des résultats ---
ROOT_FOLDER = Path(__file__).resolve().parent / "Data"
FILE = "stack"
H_SNR = ROOT_FOLDER / f"{FILE}_High_SNR.tif"
L_SNR = ROOT_FOLDER / f"{FILE}_Low_SNR.tif"  # .	Pile à faible rapport signal sur bruit, déjà alignée.
DENOISED = ROOT_FOLDER / f"{FILE}_Denoised.tif"  # .Pile débruitée après alignement.
OUTPUT_FOLDER = ROOT_FOLDER / f"{FILE}_analysis"

# --- Paramètres de détection et d'appariement ---
H_SNR_THRESHOLD = 100
DENOISED_THRESHOLD = 100
WATERSHED = False
MATCH_DISTANCE = 1.0  # .							Distance maximale entre détections, en pixels, dans un même plan.

# --- Paramètres d'ajustement ---
FIT_MODE = 3
ROI_SIZE = 7
SIGMA = 1.0
THETA = 0.0  # Angle initial en radians.

# --- Recherche du seuil débruité ---
# Le script calcule une échelle s = max(seuil automatique, 1),
# puis les bornes min(seuil automatique, s * facteur bas) et max(seuil automatique, s * facteur haut).
# Le seuil automatique est ainsi toujours inclus ; le plancher de 1 permet aussi d'explorer pour un seuil nul ou très faible.
# Les bornes ne sont pas élargies ensuite.
THRESHOLD_SEARCH_FACTORS = (0.5, 2.0)  # Facteurs bas et haut de la plage initiale de recherche.
# Une grille plus dense réduit le risque de manquer un pic étroit, au prix de plus d'appels PALM.
# Le meilleur seuil courant est ajouté si nécessaire ; les seuils déjà évalués sont ignorés.
THRESHOLD_SEARCH_SAMPLES = 17  # Points régulièrement espacés par grille, bornes incluses.
# Chaque raffinement explore l'intervalle entre les voisins du meilleur seuil courant.
# Une valeur nulle conserve uniquement l'exploration globale et l'évaluation initiale.
THRESHOLD_SEARCH_REFINEMENTS = 2  # Grilles locales après la grille globale ; pas de garantie du maximum continu.
