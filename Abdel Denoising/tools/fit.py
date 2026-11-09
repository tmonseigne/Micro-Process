"""Traitements PALM pour la détection et les ajustements croisés."""


import numpy as np
import pandas as pd
from palm_tracer.Processing import Palm, Parsing


# --------------------------------------------------
def analyze_stacks(stacks: dict[str, np.ndarray], h_snr_threshold: float, denoised_threshold: float, watershed: bool, fit: int, roi_size: int, sigma: float,
				theta: float) -> dict[str, pd.DataFrame]:
	"""
	Détecte sur les piles de référence et débruitée, puis ajuste les positions demandées.

	Les ajustements repartent tous des détections sans fit. Les identifiants sont conservés
	dans chaque famille et les échecs restent présents avec les indicateurs fournis par PALM.

	:param stacks: Trois piles uint16 de mêmes dimensions, alignées spatialement et temporellement.
	:param h_snr_threshold: Seuil de détection de la pile High SNR de référence.
	:param denoised_threshold: Seuil de détection de la pile débruitée.
	:param watershed: Active la séparation des détections par watershed.
	:param fit: Mode d'ajustement PALM, identique pour les quatre conditions.
	:param roi_size: Taille des régions d'intérêt en pixels.
	:param sigma: Sigma X initial en pixels ; le sigma Y initial vaut deux fois sigma.
	:param theta: Angle initial en radians.
	:return: Deux tables de détection et quatre tables d'ajustement, avec toutes les colonnes PALM.
	"""
	palm = Palm()
	detect_params = np.array([roi_size], dtype=float)
	# Même initialisation que Localization.get_fit_params : sigma Y initial = 2 × sigma X.
	fit_params = np.array([roi_size, sigma, 2 * sigma, theta], dtype=float)
	results = {}
	for name, threshold in (("h_snr", h_snr_threshold), ("denoised", denoised_threshold)):
		positions = palm.localization(stacks[name], threshold, watershed, 0, detect_params)
		results[f"detect_{name}"] = positions
		print(f"Détection {name} : {len(positions)} points")

	for source, target in (("h_snr", "h_snr"), ("denoised", "denoised"), ("denoised", "l_snr"), ("denoised", "h_snr")):
		positions = results[f"detect_{source}"]
		# Éviter un appel natif inutile lorsque la détection n'a produit aucun point.
		if positions.empty: fitted = pd.DataFrame(columns=Parsing.FILES_COLUMNS["Localization"]["columns"])
		else: fitted = palm.fitting(stacks[target], positions.copy(), fit, fit_params)
		results[f"fit_{source}_on_{target}"] = fitted
		print(f"Ajustement {source} sur {target} : {len(fitted)} points")
	return results
