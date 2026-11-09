"""Calcul des seuils automatiques et recherche par maximisation du Jaccard."""

import numpy as np
import pandas as pd
from palm_tracer.Processing import Palm

from .localization_analysis import get_scores


# --------------------------------------------------
def get_thresholds(stack: np.ndarray, roi_size: int) -> np.ndarray:
	"""
	Calcule un seuil automatique pour chaque plan d'une pile.

	:param stack: Pile d'images, avec les plans sur le premier axe.
	:param roi_size: Taille des régions d'intérêt en pixels.
	:return: Tableau unidimensionnel des seuils dans l'ordre des plans.
	"""
	palm = Palm()
	params = np.array([roi_size], dtype=float)
	n_planes = stack.shape[0]
	res = np.zeros(n_planes, dtype=float)
	for i in range(n_planes): res[i] = palm.auto_threshold(stack[i], params)
	return res


# --------------------------------------------------
def collect_thresholds(stacks: dict[str, np.ndarray], roi_size: int) -> pd.DataFrame:
	"""
	Calcule les seuils de chaque plan pour toutes les piles, sans export.

	:param stacks: Piles indexées par leur nom.
	:param roi_size: Taille des régions d'intérêt en pixels.
	:return: Une colonne par pile ; les plans absents sont représentés par NaN.
	"""
	return pd.DataFrame({name: pd.Series(get_thresholds(stack, roi_size)) for name, stack in stacks.items()})


# --------------------------------------------------
def find_best_threshold(stack: np.ndarray, reference: pd.DataFrame, initial_threshold: float, watershed: bool, fit: int,
						fit_params: np.ndarray, max_distance: float, bounds: tuple[float, float], samples: int = 17,
						refinements: int = 2, initial_localizations: pd.DataFrame | None = None) -> tuple[float, pd.DataFrame, list[list[float]]]:
	"""
	Recherche le seuil débruité maximisant le Jaccard par grille globale et raffinements.

	La référence est fixée par l'appelant : elle n'est pas recalculée lorsque le seuil de la pile débruitée change.
	Pour chaque seuil, PALM traite la pile entière avec les mêmes paramètres de détection et d'ajustement.
	Les localisations sont appariées un à un à la référence, dans le même plan et à une distance XY	inférieure ou égale à ``max_distance``.
	L'appariement maximise le nombre de	concordances, sans minimiser leur distance.

	Le critère à maximiser est :math:`J = TP / (TP + FP + FN)` : TP désigne les	concordances,
	FP les détections sans référence et FN les références non retrouvées.
	Deux ensembles vides donnent un Jaccard de 1, conformément à ``get_scores``.
	Ces catégories sont relatives aux localisations de référence, qui ne constituent pas nécessairement une vérité terrain.

	Méthode :

	1. Évaluer le seuil automatique initial, en réutilisant ``initial_localizations`` si elles sont fournies.
	   Cette première évaluation sert de résultat de départ.
	2. Explorer ``samples`` seuils régulièrement espacés, bornes incluses, sur tout l'intervalle ``bounds``.
	   Ajouter le meilleur seuil courant à la grille pour qu'il reste un point explicite, même s'il n'appartient pas à l'espacement choisi.
	3. Retenir le plus grand Jaccard. En cas d'égalité, privilégier le seuil le plus proche du seuil initial ; à distance égale, garder le premier évalué.
	4. Encadrer le meilleur seuil par ses voisins immédiats dans la grille triée, puis explorer cet intervalle avec une nouvelle grille de ``samples`` points.
	   Si le meilleur est à une borne, conserver cette borne et son voisin intérieur.
	5. Répéter l'étape de raffinement ``refinements`` fois après la grille globale.
	   Un intervalle réduit à un seul seuil arrête la recherche. Un plateau de score ou un Jaccard de 1 ne l'arrête pas prématurément.

	Chaque seuil distinct est évalué une seule fois ; les doublons entre les grilles sont ignorés.
	Toutes les lignes de scores restent dans l'ordre des évaluations, avec le seuil initial en premier.
	Les tables de localisations intermédiaires ne sont pas accumulées : la table du meilleur résultat est conservée pour l'export final.
	Cette fonction n'écrit aucun fichier ; le script appelant enregistre les scores et les localisations finales après le retour de la recherche.

	Le Jaccard évolue par paliers et n'est pas supposé unimodal : une recherche par gradient n'est donc pas utilisée.
	La grille globale peut manquer un pic étroit et les raffinements se concentrent sur une seule zone.
	Le résultat est le meilleur seuil parmi ceux évalués, sans garantie du maximum global entre les points ou hors des bornes initiales.
	Aucun raffinement ne sort de cet intervalle initial.

	:param stack: Pile débruitée entière, transmise à PALM à chaque évaluation.
	:param reference: Localisations de référence fixes, avec les colonnes Plane, X et Y.
	:param initial_threshold: Seuil automatique initial, fini et positif ou nul.
	:param watershed: Active la séparation des détections par watershed.
	:param fit: Mode d'ajustement PALM, conservé pour tous les seuils.
	:param fit_params: Paramètres d'ajustement identiques pour toutes les évaluations.
	:param max_distance: Distance maximale d'appariement XY en pixels, identique pour tous les seuils.
	:param bounds: Bornes finies, positives ou nulles, contenant le seuil initial.
	:param samples: Nombre de points régulièrement espacés par grille, au moins trois. Le meilleur seuil courant peut ajouter un point à la grille.
	:param refinements: Nombre de grilles locales après la grille globale ; zéro désactive le raffinement.
	:param initial_localizations: Localisations déjà calculées pour la même pile, le seuil initial et les mêmes paramètres.
		Si absentes, elles sont calculées avant la première grille.
	:return: Meilleur seuil évalué, ses localisations et toutes les lignes de scores.
		Chaque ligne contient, dans cet ordre : seuil, Jaccard, nombre de références,
		nombre de détections, vrais positifs, faux positifs et faux négatifs.
	:raises ValueError: Si les seuils, la distance ou les paramètres de grille sont invalides.
	"""
	lower, upper = bounds
	if not np.isfinite([initial_threshold, lower, upper]).all() or not 0 <= lower <= initial_threshold <= upper:
		raise ValueError("Les bornes doivent être finies, positives ou nulles et contenir le seuil initial.")
	if not np.isfinite(max_distance) or max_distance < 0:
		raise ValueError("La distance maximale doit être finie et positive ou nulle.")
	if isinstance(samples, bool) or not isinstance(samples, (int, np.integer)) or samples < 3:
		raise ValueError("Une grille doit contenir au moins trois points.")
	if isinstance(refinements, bool) or not isinstance(refinements, (int, np.integer)) or refinements < 0:
		raise ValueError("Le nombre de raffinements doit être un entier positif ou nul.")

	# Établir le score de départ ; réutiliser les localisations initiales évite un appel PALM supplémentaire.
	palm = Palm()
	best_threshold = float(initial_threshold)
	best_localizations = initial_localizations
	if best_localizations is None: best_localizations = palm.localization(stack, best_threshold, watershed, fit, fit_params)
	initial_scores = get_scores(reference, best_localizations, max_distance)
	scores = [[best_threshold, *initial_scores]]
	# Comparaison lexicographique : maximiser le Jaccard, puis minimiser la variation du seuil.
	best_key = (initial_scores[0], 0.0)
	evaluated = {best_threshold}

	# Premier passage global, puis grilles locales ; le meilleur point est toujours présent dans la grille.
	for _ in range(refinements + 1):
		grid = np.unique(np.append(np.linspace(lower, upper, samples), best_threshold))
		for candidate in grid:
			candidate = float(candidate)
			# Les bornes et le meilleur seuil peuvent être communs à plusieurs grilles.
			if candidate in evaluated: continue
			localizations = palm.localization(stack, candidate, watershed, fit, fit_params)
			current_scores = get_scores(reference, localizations, max_distance)
			# Conserver chaque évaluation, même si elle ne remplace pas le meilleur résultat.
			scores.append([candidate, *current_scores])
			evaluated.add(candidate)
			key = (current_scores[0], -abs(candidate - initial_threshold))
			# Une égalité complète ne remplace pas la première évaluation retenue.
			if key > best_key:
				best_key = key
				best_threshold = candidate
				best_localizations = localizations

		# Raffiner entre les voisins immédiats ; à une borne, seul le voisin intérieur est utilisé.
		# Aucun élargissement de la plage initiale ni critère d'arrêt fondé sur la variation du score.
		best_index = int(np.searchsorted(grid, best_threshold))
		lower = float(grid[max(0, best_index - 1)])
		upper = float(grid[min(len(grid) - 1, best_index + 1)])
		if lower == upper: break

	return best_threshold, best_localizations, scores
