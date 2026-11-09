"""Statistiques, bilans et figures des expériences sur les seuils de détection."""

from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Ordre partagé avec les lignes produites par threshold.find_best_threshold et localization_analysis.get_scores.
SCORE_COLUMNS = ["threshold", "jaccard", "reference_count", "detected_count", "true_positives", "false_positives", "false_negatives"]


# ==================================================
# region Préparation des bilans
# ==================================================
def summarize_thresholds(thresholds: pd.DataFrame) -> pd.DataFrame:
	"""
	Calcule la moyenne et l'écart-type échantillonnal des seuils de chaque pile.

	Les valeurs manquantes sont ignorées ; l'écart-type est indéfini lorsqu'une pile contient moins de deux valeurs disponibles.

	:param thresholds: Seuils par plan, avec une colonne par pile.
	:return: Statistiques indexées par nom de pile, avec Moyenne et Écart-type.
	"""
	statistics = thresholds.agg(["mean", "std"]).T
	statistics.columns = ["Moyenne", "Écart-type"]
	return statistics


# --------------------------------------------------
def prepare_scores(scores: list[list[float]]) -> pd.DataFrame:
	"""
	Construit le tableau des évaluations à partir des seuils et de leurs scores.

	:param scores: Lignes contenant le seuil suivi des valeurs de get_scores.
	:return: Tableau utilisant les colonnes de SCORE_COLUMNS.
	:raises ValueError: Si aucune évaluation n'est fournie.
	"""
	if not scores:
		raise ValueError("Aucun score disponible pour l'analyse.")
	return pd.DataFrame(scores, columns=SCORE_COLUMNS)


# --------------------------------------------------
def show_result(scores: pd.DataFrame, initial_threshold: float):
	"""
	Affiche le meilleur seuil évalué et sa variation par rapport au seuil initial.

	À Jaccard égal, le seuil le plus proche du seuil initial est retenu ; à distance égale,
	la première ligne l'emporte. Une variation relative est indéfinie si le seuil initial est nul.

	:param scores: Tableau non vide des seuils évalués et de leurs indices de Jaccard, dans l'ordre des évaluations.
	:param initial_threshold: Seuil automatique initial de la pile débruitée.
	"""
	# Le meilleur seuil maximise le Jaccard.
	# En cas d'égalité, retenir le seuil le plus proche du seuil initial.
	best_rows = scores.loc[scores["jaccard"] == scores["jaccard"].max()]
	best_index = (best_rows["threshold"] - initial_threshold).abs().idxmin()
	final_threshold = float(scores.loc[best_index, "threshold"])

	delta = final_threshold - initial_threshold
	direction = "Augmentation" if delta > 0 else "Diminution" if delta < 0 else "Inchangé"
	percentage = f"{100 * delta / initial_threshold:+.2f} %" if initial_threshold != 0 else "non défini (seuil initial nul)"

	print(f"Seuil : {direction}, initial : {initial_threshold:.6g}, final : {final_threshold:.6g}, Delta : {delta:+.6g} ({percentage})")


# ==================================================
# endregion Préparation des bilans
# ==================================================

# ==================================================
# region Rendus spéciaux
# ==================================================
def plot_threshold_distribution(data: pd.DataFrame, stack_names: list[str], output_file: Path, mode: Literal["violin", "box"] = "violin"):
	"""
	Enregistre les distributions des seuils, avec une catégorie par pile.

	:param data: Table au format long contenant les noms de piles dans Stack et leurs seuils dans Threshold.
	:param stack_names: Noms des piles dans leur ordre d'affichage.
	:param output_file: Chemin de la figure à enregistrer.
	:param mode: Représentation par violons ou boîtes à moustaches.
	"""
	# Le contexte limite les réglages esthétiques à cette figure.
	with sns.axes_style("whitegrid"), sns.plotting_context("notebook"):
		fig, ax = plt.subplots(figsize=(max(6.0, 1.5 * len(stack_names)), 5.0), layout="constrained")
		try:
			options = {"data": data, "x": "Stack", "y": "Threshold", "order": stack_names, "color": "#72A7CF", "ax": ax, }
			if mode == "violin": sns.violinplot(**options, inner="quartile", cut=0)
			else: sns.boxplot(**options, width=0.5)

			ax.set(title="Distribution des seuils automatiques", xlabel="Pile", ylabel="Seuil")
			ax.tick_params(axis="x", labelrotation=30)
			sns.despine(ax=ax)

			output_file.parent.mkdir(parents=True, exist_ok=True)
			fig.savefig(output_file, dpi=300, bbox_inches="tight")
		finally: plt.close(fig)


# --------------------------------------------------
def plot_scores(scores: pd.DataFrame, output_file: Path):
	"""
	Enregistre le Jaccard et les effectifs pour chaque seuil évalué.

	Le tri par seuil sert uniquement au tracé ; le tableau reçu n'est pas modifié.

	:param scores: Tableau contenant les colonnes définies par SCORE_COLUMNS.
	:param output_file: Chemin de la figure à enregistrer.
	"""
	output_file.parent.mkdir(parents=True, exist_ok=True)
	# Le tri concerne uniquement la représentation graphique.
	data = scores.sort_values("threshold")

	with sns.axes_style("whitegrid"), sns.plotting_context("notebook"):
		fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True, layout="constrained")
		try:
			axes[0].plot(data["threshold"], data["jaccard"], marker="o")
			axes[0].set(title="Qualité des localisations", ylabel="Indice de Jaccard", ylim=(-0.02, 1.02))

			for column, label in (("reference_count", "Référence"), ("detected_count", "Détections"), ("true_positives", "Vrais positifs (TP)"),
								  ("false_positives", "Faux positifs (FP)"), ("false_negatives", "Faux négatifs (FN)")):
				axes[1].plot(data["threshold"], data[column], marker="o", label=label)

			axes[1].set(xlabel="Seuil", ylabel="Nombre de localisations")
			axes[1].legend()
			sns.despine(fig=fig)
			fig.savefig(output_file, dpi=300, bbox_inches="tight", )
		finally: plt.close(fig)

# ==================================================
# endregion Rendus spéciaux
# ==================================================
