"""
Appariement et qualité des détections relativement à une référence.

Les scores utilisent un appariement de cardinalité maximale. Le bilan d'une
table combinée réutilise ses statuts, sans effectuer un nouvel appariement.
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
from scipy.spatial import cKDTree


# --------------------------------------------------
def get_scores(a: pd.DataFrame, b: pd.DataFrame, max_distance: float) -> list[float]:
	"""
	Compare des localisations par appariement spatial un à un, plan par plan.

	Les tables vides sont acceptées, y compris sans colonnes.
	Deux tables vides donnent un Jaccard de 1 ; une seule table vide donne 0.
	Les références absentes sont les faux négatifs et les détections supplémentaires les faux positifs.

	L'appariement maximise le nombre de paires séparées d'une distance inférieure ou égale à ``max_distance``. Il ne minimise pas leur distance.

	:param a: Localisations de référence, avec les colonnes Plane, X et Y.
	:param b: Localisations évaluées, avec les mêmes colonnes.
	:param max_distance: Distance XY maximale entre deux points, en pixels.
	:return: Jaccard, effectifs de référence et détecté, vrais positifs,
		faux positifs et faux négatifs, dans cet ordre.
	:raises ValueError: Si la distance ou les coordonnées sont invalides.
	"""
	if not np.isfinite(max_distance) or max_distance < 0: raise ValueError("La distance maximale doit être finie et positive ou nulle.")

	for localizations in (a, b):
		if not localizations.empty:
			values = localizations[["Plane", "X", "Y"]].to_numpy(dtype=float)
			if not np.isfinite(values).all(): raise ValueError("Les plans et les coordonnées doivent être finis.")

	true_positives = 0
	if not a.empty and not b.empty:
		groups_b = dict(tuple(b.groupby("Plane", sort=False)))

		for plane, group_a in a.groupby("Plane", sort=False):
			group_b = groups_b.get(plane)
			if group_b is None: continue

			xy_a = group_a[["X", "Y"]].to_numpy(dtype=float)
			xy_b = group_b[["X", "Y"]].to_numpy(dtype=float)

			# Le graphe ne contient que les paires respectant la distance.
			neighbors = cKDTree(xy_a).query_ball_tree(cKDTree(xy_b), r=max_distance)
			lengths = np.fromiter((len(indices) for indices in neighbors), dtype=np.intp, count=len(xy_a))
			if lengths.sum() == 0: continue

			columns = np.concatenate([np.asarray(indices, dtype=np.intp) for indices in neighbors])
			indptr = np.concatenate(([0], np.cumsum(lengths)))
			graph = csr_matrix((np.ones(columns.size, dtype=np.uint8), columns, indptr), shape=(len(xy_a), len(xy_b)), )

			assignment = maximum_bipartite_matching(graph, perm_type="column")
			true_positives += int(np.count_nonzero(assignment >= 0))

	reference_count = len(a)
	detected_count = len(b)
	false_positives = detected_count - true_positives
	false_negatives = reference_count - true_positives
	union = true_positives + false_positives + false_negatives

	# Convention : deux ensembles vides sont identiques.
	jaccard = true_positives / union if union else 1.0

	return [jaccard, reference_count, detected_count, true_positives, false_positives, false_negatives]


# --------------------------------------------------
def summarize_localizations(combined: pd.DataFrame) -> pd.DataFrame:
	"""
	Compte les détections et les erreurs d'appariement en prenant le High SNR comme référence.

	Les faux positifs sont les détections présentes uniquement après débruitage ;
	les faux négatifs sont les détections High SNR sans correspondant après débruitage.
	Ces catégories dépendent du seuil de détection et de la distance utilisée pour construire la table, sans constituer une vérité terrain.

	:param combined: Table combinée contenant la colonne Status.
	:return: Une ligne de statistiques ; les pourcentages sans dénominateur sont NaN.
	"""
	counts = combined["Status"].value_counts()
	matched = int(counts.get("matched", 0))
	false_positives = int(counts.get("denoised_only", 0))
	false_negatives = int(counts.get("h_snr_only", 0))
	high_count = matched + false_negatives
	denoised_count = matched + false_positives
	return pd.DataFrame([{"High SNR Localizations":       high_count,
						  "Denoised Localizations":       denoised_count,
						  "Matched Localizations":        matched,
						  "False Positives":              false_positives,
						  "False Negatives":              false_negatives,
						  "False Positives (% Denoised)": 100 * false_positives / denoised_count if denoised_count else np.nan,
						  "False Negatives (% High SNR)": 100 * false_negatives / high_count if high_count else np.nan}])
