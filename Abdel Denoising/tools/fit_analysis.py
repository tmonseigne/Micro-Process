"""Comparaison des ajustements croisés après débruitage, à partir des tables PALM."""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# Ordre des quatre conditions et libellés utilisés pour les statistiques et les figures.
FIT_GROUPS = {"fit_h_snr_on_h_snr":       "H → H (référence)",
			  "fit_denoised_on_denoised": "D → D",
			  "fit_denoised_on_l_snr":    "D → L",
			  "fit_denoised_on_h_snr":    "D → H"}


# ==================================================
# region Appariement et combinaison des résultats
# ==================================================
def combine_results(results: dict[str, pd.DataFrame], max_distance: float) -> pd.DataFrame:
	"""
	Combine les détections et tous leurs ajustements, en conservant les points sans correspondant.

	L'appariement utilise les positions sans fit, séparément pour chaque plan.
	Les couples	admissibles sont traités par distance croissante ; chaque détection est utilisée au plus une fois.
	Ce choix glouton privilégie les voisins les plus proches, sans optimisation globale.
	Les ajustements sont joints par identifiant, car leurs positions et leur ordre peuvent changer.
	Les colonnes de chaque table sont préfixées par son nom ; une table absente pour un point est remplie avec -1.
	Les valeurs d'un ajustement existant sont conservées telles quelles.
	Les détections contribuent uniquement leurs coordonnées X et Y ; les mesures ajustées sont conservées pour les fits.
	Les identifiants servent uniquement aux jointures. Le plan est indiqué une seule fois dans la colonne commune Plane.

	:param results: Deux tables de détection et quatre tables d'ajustement issues de l'analyse.
	:param max_distance: Distance maximale d'appariement en pixels.
	:return: Table combinée avec statut, distance et mesures sélectionnées des six tables.
	"""
	high = results["detect_h_snr"].reset_index(drop=True)
	denoised = results["detect_denoised"].reset_index(drop=True)
	rows = []
	planes = sorted(set(high["Plane"]) | set(denoised["Plane"]))
	for plane in planes:
		h = high.loc[high["Plane"] == plane]
		d = denoised.loc[denoised["Plane"] == plane]
		candidates = []
		if not h.empty and not d.empty:
			h_xy, d_xy = h[["X", "Y"]].to_numpy(), d[["X", "Y"]].to_numpy()
			neighbors = cKDTree(d_xy).query_ball_point(h_xy, max_distance)
			for i, nearby in enumerate(neighbors):
				for j in nearby: candidates.append((float(np.linalg.norm(h_xy[i] - d_xy[j])), i, j))
		used_h, used_d = set(), set()
		for distance, i, j in sorted(candidates):
			if i in used_h or j in used_d: continue
			used_h.add(i)
			used_d.add(j)
			rows.append((plane, "matched", distance, h.iloc[i]["Id"], d.iloc[j]["Id"]))
		for i, point_id in enumerate(h["Id"]):
			if i not in used_h: rows.append((plane, "h_snr_only", -1, point_id, -1))
		for j, point_id in enumerate(d["Id"]):
			if j not in used_d: rows.append((plane, "denoised_only", -1, -1, point_id))

	combined = pd.DataFrame(rows, columns=["Plane", "Status", "Match Distance", "High SNR Id", "Denoised Id"])
	for name, table in results.items():
		id_column = "High SNR Id" if name in ("detect_h_snr", "fit_h_snr_on_h_snr") else "Denoised Id"
		# Le réindexage conserve les lignes même si le parsing PALM a retiré un ajustement invalide.
		indexed = table.set_index("Id", drop=False)
		ids = combined[id_column]
		block = indexed.reindex(ids).reset_index(drop=True)
		block.loc[~ids.isin(indexed.index)] = -1
		columns = (["X", "Y"] if name.startswith("detect_") else ["X", "Y", "Integrated Intensity", "Sigma X", "Sigma Y", "MSE XY"])
		block = block[columns]
		combined = pd.concat([combined, block.add_prefix(f"{name}__")], axis=1)
	return combined.drop(columns=["High SNR Id", "Denoised Id"])


# ==================================================
# endregion Appariement et combinaison des résultats
# ==================================================

# ==================================================
# region Validité et statistiques des ajustements
# ==================================================
def valid_fit_mask(table: pd.DataFrame) -> np.ndarray:
	"""
	Identifie les fits finis avec coordonnées, intensité et sigmas positifs, et MSE non négatif.

	:param table: Paramètres X, Y, Integrated Intensity, Sigma X, Sigma Y et MSE XY.
	:return: Masque des fits exploitables, excluant notamment les sentinelles -1 et les sorties nulles.
	"""
	positive = ["X", "Y", "Integrated Intensity", "Sigma X", "Sigma Y"]
	return np.isfinite(table.to_numpy()).all(axis=1) & table[positive].gt(0).all(axis=1).to_numpy() & table["MSE XY"].ge(0).to_numpy()


# --------------------------------------------------
def summarize_fit_failures(combined: pd.DataFrame) -> pd.DataFrame:
	"""
	Compte les fits non exploitables séparément pour chaque condition, même hors appariement.

	Une détection absente n'est pas une tentative de fit. Une sortie retirée par PALM ou ne satisfaisant pas :func:`valid_fit_mask` est comptée comme échec ;
	aucun code natif de convergence n'étant exporté, ce bilan décrit la validité des sorties disponibles.

	:param combined: Table combinée des détections et ajustements.
	:return: Tentatives, réussites, échecs, taux d'échec et échecs sur les points appariés par fit.
	"""
	rows = []
	for name in FIT_GROUPS:
		table = combined.filter(like=f"{name}__").copy()
		table.columns = table.columns.str.removeprefix(f"{name}__")
		absent = "denoised_only" if name == "fit_h_snr_on_h_snr" else "h_snr_only"
		attempted = combined["Status"].ne(absent).to_numpy()
		valid = valid_fit_mask(table)
		failed = attempted & ~valid
		count = int(attempted.sum())
		rows.append({"Fit":            name, "Attempted": count, "Successful": int((attempted & valid).sum()),
					 "Failed":         int(failed.sum()), "Failed (%)": 100 * failed.sum() / count if count else np.nan,
					 "Failed Matched": int((failed & combined["Status"].eq("matched").to_numpy()).sum())})
	return pd.DataFrame(rows)


# --------------------------------------------------
def prepare_fit_comparison(combined: pd.DataFrame) -> dict[str, pd.DataFrame]:
	"""
	Sélectionne une cohorte commune et calcule les déplacements par rapport au fit High SNR.

	Seuls les points appariés, finis et valides dans les quatre fits sont conservés : intensité
	intégrée et sigmas strictement positifs, MSE positif ou nul, coordonnées positives.
	Les déplacements sont exprimés en pixels ; la référence est un fit, pas une vérité terrain.

	:param combined: Table combinée des détections et ajustements.
	:return: Une table par fit, avec paramètres et distance euclidienne XY à la référence.
	"""
	columns = ["X", "Y", "Integrated Intensity", "Sigma X", "Sigma Y", "MSE XY"]
	valid = combined["Status"].eq("matched").to_numpy(copy=True)
	comparison = {}
	for name in FIT_GROUPS:
		table = combined[[f"{name}__{column}" for column in columns]].copy()
		table.columns = columns
		valid &= valid_fit_mask(table)
		comparison[name] = table
	comparison = {name: table.loc[valid].reset_index(drop=True) for name, table in comparison.items()}
	reference = comparison["fit_h_snr_on_h_snr"]
	for table in comparison.values(): table["XY Distance"] = np.hypot(table["X"] - reference["X"], table["Y"] - reference["Y"])
	print(f"Comparaison des fits : {int(valid.sum())}/{int(combined['Status'].eq('matched').sum())} points appariés valides dans les quatre conditions.")
	return comparison


# --------------------------------------------------
def summarize_fits(comparison: dict[str, pd.DataFrame], differences: bool = False) -> pd.DataFrame:
	"""
	Résume chaque paramètre et ses écarts au fit High SNR sur la cohorte commune.

	:param comparison: Tables produites par :func:`prepare_fit_comparison`.
	:param differences: Résume les différences signées fit moins référence, en excluant la référence.
		La position reste une distance euclidienne positive, jamais un écart par axe.
	:return: Effectif, moyenne, écart-type échantillonnal, quantiles, extrêmes, biais et RMSE
		par paramètre et condition. Les statistiques indéfinies restent NaN.
	"""
	reference = comparison["fit_h_snr_on_h_snr"]
	rows = []
	for name, table in comparison.items():
		if differences and name == "fit_h_snr_on_h_snr": continue
		for parameter in ("XY Distance", "Integrated Intensity", "Sigma X", "Sigma Y", "MSE XY"):
			difference = table[parameter] - reference[parameter]
			values = difference if differences else table[parameter]
			rows.append({"Fit":              name, "Parameter": parameter, "Count": len(values),
						 "Mean":             values.mean(), "Std": values.std(), "Median": values.median(),
						 "Q25":              values.quantile(0.25), "Q75": values.quantile(0.75),
						 "Min":              values.min(), "Max": values.max(),
						 "Bias vs High SNR": difference.mean(), "RMSE vs High SNR": np.sqrt(difference.pow(2).mean())})
	return pd.DataFrame(rows)


# ==================================================
# endregion Validité et statistiques des ajustements
# ==================================================

# ==================================================
# region Rendus spéciaux
# ==================================================
def plot_fit_comparison(comparison: dict[str, pd.DataFrame], filename: Path, differences: bool = False):
	"""
	Trace les distributions des paramètres ou leurs différences au fit High SNR de référence.

	Les boîtes montrent médiane et quartiles ; les moustaches s'étendent jusqu'à 1,5 IQR.
	Les points hors moustaches restent visibles ; toute la cohorte commune est utilisée.
	La position est toujours représentée par la distance euclidienne entre les deux fits.
	En mode différences, chaque panneau contient trois boîtes, avec delta = fit moins référence
	pour les paramètres scalaires et une ligne zéro permettant de lire le sens du biais.

	:param comparison: Tables de la cohorte commune.
	:param filename: Chemin de la figure PNG à enregistrer.
	:param differences: Compare les trois autres fits à la référence au lieu des valeurs brutes.
	"""
	count = len(comparison["fit_h_snr_on_h_snr"])
	if count == 0:
		print("Aucune figure des fits : aucun point commun valide.")
		return
	fig, axes = plt.subplots(2, 3, figsize=(17, 10), layout="constrained")
	colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
	reference = comparison["fit_h_snr_on_h_snr"]
	panels = [("XY Distance", "Distance au fit H → H (pixels)"), ("Integrated Intensity", "Intensité intégrée (unités PALM)"),
			  ("Sigma X", "Sigma X (pixels)"), ("Sigma Y", "Sigma Y (pixels)"), ("MSE XY", "MSE XY (unités PALM)")]
	# Le sixième panneau est réservé au texte ; les cinq paramètres occupent les premiers axes.
	for ax, (parameter, title) in zip(axes.flat, panels, strict=False):
		groups = [name for name in FIT_GROUPS if name != "fit_h_snr_on_h_snr" or not (differences or parameter == "XY Distance")]
		values = [(comparison[name][parameter] - reference[parameter] if differences else comparison[name][parameter]).to_numpy() for name in groups]
		boxes = ax.boxplot(values, patch_artist=True, flierprops={"markersize": 2, "alpha": 0.25})
		for box, name in zip(boxes["boxes"], groups, strict=False):
			color = colors[list(FIT_GROUPS).index(name)]
			box.set_facecolor(color)
			box.set_alpha(0.5)
		ax.set_xticks(range(1, len(groups) + 1), [FIT_GROUPS[name] for name in groups])
		ax.set_title(f"Δ {title}" if differences and parameter != "XY Distance" else title)
		if differences: ax.axhline(0, color="grey", linewidth=0.7, linestyle="--")
		ax.grid(axis="y", alpha=0.25)
	axes[1, 2].axis("off")
	axes[1, 2].text(0.05, 0.8, "Référence : fit H → H\n\nPosition : distance euclidienne (pixels)\n"
							   "Paramètres : fit − référence" if differences else "Référence de position : fit H → H\n\nParamètres : valeurs brutes",
					transform=axes[1, 2].transAxes, va="top", fontsize=12)
	mode = "Écarts au fit H → H" if differences else "Comparaison des quatre fits"
	fig.suptitle(f"{mode} — {count} points communs valides\n"
				 "H : High SNR ; D : débruité ; L : Low SNR — détection → image ajustée")
	fig.savefig(filename, dpi=180)
	plt.close(fig)

# ==================================================
# endregion Rendus spéciaux
# ==================================================
