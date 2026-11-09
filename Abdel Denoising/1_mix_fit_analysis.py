"""Compare les détections et les ajustements après débruitage."""

from params import DENOISED, DENOISED_THRESHOLD, FIT_MODE, H_SNR, H_SNR_THRESHOLD, L_SNR, MATCH_DISTANCE, OUTPUT_FOLDER, ROI_SIZE, SIGMA, THETA, WATERSHED
from tools import fit, fit_analysis, io, localization_analysis


# --------------------------------------------------
def main():
	"""Compare les détections, puis les quatre ajustements sur une cohorte commune."""
	OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

	# --- Charger les trois conditions alignées ---
	paths = {"h_snr": H_SNR, "l_snr": L_SNR, "denoised": DENOISED}
	stacks = io.load_stacks(paths)

	# --- Détecter puis ajuster les mêmes positions dans les différentes conditions ---
	results = fit.analyze_stacks(stacks, H_SNR_THRESHOLD, DENOISED_THRESHOLD, WATERSHED, FIT_MODE, ROI_SIZE, SIGMA, THETA)
	for name, table in results.items(): io.save_table(table, OUTPUT_FOLDER / f"{name}.csv")

	# --- Apparier les détections et mesurer les faux positifs et faux négatifs ---
	combined = fit_analysis.combine_results(results, MATCH_DISTANCE)
	io.save_table(combined, OUTPUT_FOLDER / "combined.csv")
	statistics = localization_analysis.summarize_localizations(combined)
	io.save_table(statistics, OUTPUT_FOLDER / "statistics.csv")
	print(statistics.T.to_string(header=False))

	# --- Distinguer les échecs d'ajustement des détections absentes ---
	failures = fit_analysis.summarize_fit_failures(combined)
	io.save_table(failures, OUTPUT_FOLDER / "fit_failures.csv")
	print(failures.to_string(index=False))

	# --- Comparer les fits valides sur les mêmes points ---
	comparison = fit_analysis.prepare_fit_comparison(combined)
	fit_statistics = fit_analysis.summarize_fits(comparison)
	io.save_table(fit_statistics, OUTPUT_FOLDER / "fit_statistics.csv")
	delta_statistics = fit_analysis.summarize_fits(comparison, differences=True)
	io.save_table(delta_statistics, OUTPUT_FOLDER / "fit_delta_statistics.csv")

	# --- Visualiser les valeurs et les écarts par rapport à la référence ---
	fit_analysis.plot_fit_comparison(comparison, OUTPUT_FOLDER / "fit_comparison.png")
	fit_analysis.plot_fit_comparison(comparison, OUTPUT_FOLDER / "fit_deltas.png", differences=True)
	print(f"Résultats enregistrés dans {OUTPUT_FOLDER}")


if __name__ == "__main__":
	main()
