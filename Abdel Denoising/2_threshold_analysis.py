"""Recherche le seuil du débruitage maximisant le Jaccard face à la référence."""

import numpy as np
from palm_tracer.Processing import Palm

from params import (DENOISED, FIT_MODE, H_SNR, MATCH_DISTANCE, OUTPUT_FOLDER, ROI_SIZE, SIGMA, THETA,
					THRESHOLD_SEARCH_FACTORS, THRESHOLD_SEARCH_REFINEMENTS, THRESHOLD_SEARCH_SAMPLES, WATERSHED, )
from tools import io, threshold, threshold_analysis


# --------------------------------------------------
def main():
	"""Analyse les seuils automatiques, recherche le meilleur seuil et exporte les localisations finales."""
	OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

	# --- Charger la référence et l'image débruitée alignées ---
	stacks = io.load_stacks({"h_snr": H_SNR, "denoised": DENOISED})

	# --- Calculer et comparer les seuils automatiques de chaque plan ---
	thresholds = threshold.collect_thresholds(stacks, ROI_SIZE)
	threshold_data = thresholds.melt(var_name="Stack", value_name="Threshold").dropna(subset=["Threshold"])
	if threshold_data.empty:
		raise ValueError("Aucun seuil disponible pour l'analyse.")
	io.save_table(threshold_data, OUTPUT_FOLDER / "auto_thresholds.csv")
	statistics = threshold_analysis.summarize_thresholds(thresholds)
	io.save_table(statistics, OUTPUT_FOLDER / "auto_threshold_statistics.csv")
	print(statistics.to_string(float_format=lambda value: f"{value:.3f}"))
	threshold_analysis.plot_threshold_distribution(threshold_data, thresholds.columns.tolist(), OUTPUT_FOLDER / "auto_threshold_distribution.png")

	# --- Localiser au seuil automatique moyen de chaque condition ---
	# La référence High SNR est calculée une seule fois : seul le seuil débruité varie ensuite.
	threshold_h = float(statistics.loc["h_snr", "Moyenne"])
	threshold_d = float(statistics.loc["denoised", "Moyenne"])
	palm = Palm()
	fit_params = np.array([ROI_SIZE, SIGMA, 2 * SIGMA, THETA], dtype=float)
	loc_h = palm.localization(stacks["h_snr"], threshold_h, WATERSHED, FIT_MODE, fit_params)
	io.save_table(loc_h, OUTPUT_FOLDER / "localisation_h_snr.csv")
	loc_d = palm.localization(stacks["denoised"], threshold_d, WATERSHED, FIT_MODE, fit_params)
	io.save_table(loc_d, OUTPUT_FOLDER / "localisation_d.csv")

	# --- Rechercher le meilleur seuil en conservant la référence et les paramètres ---
	# Voir la méthodologie détaillée dans threshold.find_best_threshold : grille globale, puis raffinements entre les voisins du meilleur Jaccard.
	# Les facteurs et le budget de grilles sont définis dans params.py ; le maximum entre les points n'est pas garanti.
	# Le plancher d'échelle permet d'explorer même pour un seuil automatique nul ou inférieur à 1.
	search_scale = max(threshold_d, 1.0)
	search_bounds = (min(threshold_d, search_scale * THRESHOLD_SEARCH_FACTORS[0]), max(threshold_d, search_scale * THRESHOLD_SEARCH_FACTORS[1]))
	best_threshold, final_localizations, scores = threshold.find_best_threshold(
			stacks["denoised"], loc_h, threshold_d, WATERSHED, FIT_MODE, fit_params, MATCH_DISTANCE, search_bounds,
			THRESHOLD_SEARCH_SAMPLES, THRESHOLD_SEARCH_REFINEMENTS, loc_d)
	# La table finale provient directement de l'évaluation retenue, sans nouveau calcul PALM.
	io.save_table(final_localizations, OUTPUT_FOLDER / "localisation_final.csv")
	# Exporter toutes les évaluations dans leur ordre de calcul, y compris le seuil initial.
	# Les fichiers sont écrits après la recherche ; ils ne constituent pas une sauvegarde en cours d'exécution.
	scores_df = threshold_analysis.prepare_scores(scores)
	io.save_table(scores_df, OUTPUT_FOLDER / "scores.csv")
	threshold_analysis.plot_scores(scores_df, OUTPUT_FOLDER / "threshold_scores.png")
	threshold_analysis.show_result(scores_df, threshold_d)
	print(f"Recherche : {len(scores_df)} seuils évalués dans {search_bounds}, meilleur seuil : {best_threshold:.6g}")
	print(f"Résultats enregistrés dans {OUTPUT_FOLDER}")


if __name__ == "__main__":
	main()
