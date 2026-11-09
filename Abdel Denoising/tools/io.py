"""Chargement des piles et enregistrement des tables des expériences."""
from pathlib import Path

import numpy as np
import pandas as pd
from palm_tracer.Tools import FileIO


# --------------------------------------------------
def load_stacks(paths: dict[str, Path]) -> dict[str, np.ndarray]:
	"""
	Charge les piles demandées sans modifier leurs intensités.

	:param paths: Chemins des piles indexés par leur rôle dans la comparaison.
	:return: Piles indexées par leur rôle dans la comparaison.
	"""
	stacks = {}
	for name, path in paths.items():
		stack = FileIO.open_tif(path)
		stacks[name] = stack
		print(f"{name} : {stack.shape}, {stack.dtype}")
	return stacks


# --------------------------------------------------
def save_table(table: pd.DataFrame, output_file: Path):
	"""
	Enregistre une table CSV sans index, en UTF-8 avec des fins de lignes LF.

	Aucun arrondi n'est appliqué aux valeurs numériques.

	:param table: Table à enregistrer.
	:param output_file: Chemin du fichier CSV de destination.
	"""
	output_file.parent.mkdir(parents=True, exist_ok=True)
	table.to_csv(output_file, index=False, encoding="utf-8", lineterminator="\n")
