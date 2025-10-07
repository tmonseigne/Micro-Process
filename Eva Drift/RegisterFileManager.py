"""
Classe de gestion des fichiers Register.
"""
import contextlib
import os
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Dict, NamedTuple, Optional, Tuple

import numpy as np
import pandas as pd
from colorama import Fore, Style
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

# Constantes
COLOR_OK = Fore.GREEN
COLOR_ERR = Fore.RED
COLOR_WRN = Fore.YELLOW
COLOR_RESET = Style.RESET_ALL

# Type de retour : pos -> pile -> Prefixe dossier original -> chemin ou None
ColorDict = Dict[str, Optional[Path]]
StackDict = Dict[int, ColorDict]
FilesIndex = Dict[int, StackDict]

REGISTER_COLS = {"Track":                "Int64", "Plane": "Int64",
				 "CentroidX(px)":        "float64", "CentroidY(px)": "float64", "CentroidZ(um)": "float64",
				 "Integrated_Intensity": "float64"}


##################################################
class LinkResult(NamedTuple):
	map_ref_to_cur_pos: NDArray[int]  # (R,) positions colonne (0..C-1) ou -1
	map_ref_to_cur_id: NDArray[int]	  # (R,) IDs (index) côté courant ou -1
	deltas: NDArray[float]			  # (R, d) Δ = mean_cur - mean_ref ; NaN si -1
	used_cols: Tuple[str, ...]		  # colonnes utilisées ('CentroidX(px)', ...)


##################################################
@dataclass
class RegisterFileManager:
	""" Classe de gestion des fichiers Register. """

	_file: Optional[Path] = field(init=False, default=None)
	"""Chemin vers le fichier original."""
	_header: Optional[list[str]] = field(init=False, default=None)
	"""Header du fichier."""
	_dataframe: Optional[pd.DataFrame] = field(init=False, default=None)
	"""Dataframe du fichier."""
	_track_pos: Optional[pd.DataFrame] = field(init=False, default=None)
	"""Position de chaque trajectoire du fichier."""
	_n_smooth: int = 5
	"""Nombre de points à prendre en compte pour moyenner la position de la trajectoire."""

	##################################################
	def open(self, path: Path, header_lines: int = 2):
		"""
		Ouvre un fichier Register.txt contenant :
			  1) deux lignes d'en-tête “spéciales” à conserver telles quelles,
			  2) (éventuellement après des lignes vides) un tableau tabulé dont la première ligne est l’entête de colonnes.

		Parse le fichier pour remplir les membre dataframe et header.
		Les `header_lines` premières lignes **inchangées** (avec retours à la ligne), prêtes à être réécrites via `writelines(headers)`.

		:param path: Chemin du fichier Register.txt.
		:param header_lines: Nombre de lignes d’en-tête à conserver (par défaut 2).
		:raise FileNotFoundError: si le fichier n’existe pas.
		:raise ValueError: si le fichier ne contient pas les `header_lines` demandées.
		"""
		self._file = path
		if not path.exists() or not path.is_file(): raise FileNotFoundError(f"Fichier introuvable : {path}")
		# Lecture tolérante à l’encodage (BOM pris en charge)
		try: raw = path.read_text(encoding="utf-8")
		except UnicodeDecodeError: raw = path.read_text(encoding="cp1252")

		lines = raw.splitlines(keepends=True)  # conserve exactement les sauts de ligne
		if len(lines) < header_lines: raise ValueError(f"Fichier trop court : {len(lines)} lignes, attendu ≥ {header_lines}")
		self._header = lines[:header_lines]	   # à réécrire tels quels dans la sortie finale

		# Cherche la première ligne non vide après l’en-tête = entête du tableau
		i = header_lines
		while i < len(lines) and lines[i].strip() == "": i += 1

		# Aucun tableau
		if i >= len(lines): raise ValueError(f"Aucun tableau dans le fichier")

		table_block = "".join(lines[i:])
		try:
			self._dataframe = pd.read_csv(StringIO(table_block), sep="\t", dtype=REGISTER_COLS)
		except Exception:
			raise ValueError(f"Erreur lors de la lecture des trajectoires.")

	##################################################
	def save(self, file: Optional[Path] = None):
		"""
		Sauvegarde (écrase si aucun chemin) un Register.txt avec :
			  1) les lignes d’en-tête fournies (réécrites à l’identique),
			  2) le DataFrame `data` au format TSV (tabulations, sans index).

			La fonction écrit dans un fichier temporaire puis remplace atomiquement le fichier cible pour éviter toute corruption en cas d’erreur.

		:raise AttributeError: Erreur lors de la sauvegarde si l'on tente avant d'avoir ouvert un fichier
		:raise OSError: Erreur lors de l'écriture du fichier (espace manquant, conflit, droits d'accès...)
		"""
		if self._file is None or self._dataframe is None or self._header is None:
			raise AttributeError("Aucun fichier n'a été chargé")
		if file is None: file = self._file

		# Normalise les fins de ligne de l’en-tête (garantit un \n final par ligne au cas où)
		fixed_header = [h if h.endswith(("\n", "\r", "\r\n")) else (h + "\n") for h in self._header]

		tmp = file.with_suffix(file.suffix + ".tmp")
		try:
			# newline='' évite les lignes vides supplémentaires sous Windows
			with open(tmp, "w", encoding="utf-8", newline="") as f:
				f.writelines(fixed_header)
				# lineterminator='\n' pour des fins de ligne stables
				self._dataframe.to_csv(f, sep="\t", index=False, lineterminator="\n")
				f.flush()
				os.fsync(f.fileno())  # assure l’écriture disque avant le replace

			# Remplacement atomique (même volume)
			os.replace(tmp, file)
		except (OSError, UnicodeError) as e:
			# Nettoyage silencieux du temporaire
			with contextlib.suppress(OSError, FileNotFoundError):
				tmp.unlink(missing_ok=True)
			raise OSError(f"Échec d'écriture du fichier {file}") from e

	##################################################
	def compute_track_pos(self, n: int = 5):
		"""
		Calcule, pour chaque trajectoire (colonne « Track »), la moyenne des positions
		X/Y/Z sur les n premières lignes de cette trajectoire.
		- Les « n premières lignes » sont déterminées après tri croissant par (« Track », « Plane »)
		- Si une piste contient moins de n lignes, la moyenne est faite sur les lignes disponibles.
		- Les NaN sont ignorés par pandas lors des moyennes (skipna=True).

		:param n: Nombre de lignes à considérer par piste (n ≥ 1).
		:raise ValueError: Dataframe incompatible avec le template
		"""
		if n < 1: raise ValueError("n doit être ≥ 1")
		self._n_smooth = n
		required = list(REGISTER_COLS.keys())
		missing = [c for c in required if c not in self._dataframe.columns]
		if missing: raise ValueError(f"Colonnes manquantes : {missing}")
		df = self._dataframe[required].copy()
		# Conversion prudente au cas où des colonnes seraient typées 'object' (évite les surprises si des valeurs non-numériques se glissent)
		for c in required: df[c] = pd.to_numeric(df[c], errors='coerce')
		# Tri stable pour définir un ordre temporel/spatial cohérent par piste (optionnel normalement on est sensé être déjà trié)
		df.sort_values(['Track', 'Plane'], kind='mergesort', inplace=True)

		# Sélection des n premières lignes par piste
		head_n = df.groupby('Track', sort=False, group_keys=False).head(n)

		# Moyennes par piste sur X/Y/Z
		self._track_pos = head_n.groupby('Track', sort=True)[['CentroidX(px)', 'CentroidY(px)', 'CentroidZ(um)']].mean()

	##################################################
	def align(self, ref: "RegisterFileManager", remove_unlink: bool = False, use_3d: bool = False):
		"""
    	Aligne spatialement ce fichier sur la référence `ref` piste par piste.
		    - Δ = mean_cur - mean_ref est appliqué à TOUTES les lignes de la piste.
		    - Les IDs de Track sont renommés pour matcher ceux de la ref (1 -> 1, 2 -> 2, ...).
		    - Les pistes non liées sont supprimées (option) ou renumérotées à la suite.

		:param ref: Trajectoire de référence
		:param remove_unlink: Si True, supprime les trajectoires du fichier qui ne correspondent à aucune trajectoire de réference.
		:param use_3d: Si True, la distance inclut Z (X,Y,Z). Sinon 2D (X,Y).
		"""
		if self._dataframe is None or self._track_pos is None:
			raise AttributeError("Le fichier doit-être chargé et les positions de chaque trajectoires calculées.")
		if ref._dataframe is None or ref._track_pos is None:
			raise AttributeError("Le fichier de référence doit-être chargé et les positions de chaque trajectoires calculées.")

		# Réupération des liens entre les trajectoires des deux fichiers
		links = self._get_links(ref._track_pos, use_3d)
		cols = list(links.used_cols)

		df = self._dataframe.copy()
		df['Track'] = pd.to_numeric(df['Track'], errors='raise').astype(int)  # Au cas où mais techniquement inutile
		track = df['Track'].astype(int)

		# Appliquer Δ à toutes les lignes (piste par piste)
		valid = links.map_ref_to_cur_id != -1
		ids_cur_matched = links.map_ref_to_cur_id[valid]
		deltas_matched = links.deltas[valid]  # (M, d)

		for k, col in enumerate(cols):
			delta_map_k = {int(tid): float(deltas_matched[i, k]) for i, tid in enumerate(ids_cur_matched)}
			df[col] = df[col].to_numpy() - track.map(delta_map_k).fillna(0.0).to_numpy()

		# Optionnel : supprimer les pistes non liées
		if remove_unlink:
			keep_ids = set(int(t) for t in ids_cur_matched)
			df = df[df['Track'].isin(keep_ids)].copy()

		# Renommer les IDs de Track pour coller à la ref
		ref_ids = ref._track_pos.index.to_numpy(copy=False)  # déjà trié et suivi
		rename_map: dict[int, int] = {}
		# cur_id -> ref_id pour tous les appariés
		for r, cur_id in enumerate(links.map_ref_to_cur_id):
			if cur_id != -1:
				rename_map[int(cur_id)] = int(ref_ids[r])

		# Donner de nouveaux IDs aux non-liés, à la suite des IDs de la ref
		if not remove_unlink:
			all_cur_ids = set(df['Track'].unique().tolist())
			linked_cur_ids = set(rename_map.keys())
			unlinked_ids = sorted(all_cur_ids - linked_cur_ids)
			next_id = (int(ref_ids.max()) + 1) if len(ref_ids) else 1
			for tid in unlinked_ids:
				rename_map[int(tid)] = next_id
				next_id += 1

		# Appliquer le renommage (vectorisé, pas de collision car mapping bijectif sur les liés)
		df['Track'] = df['Track'].map(rename_map).astype(int)
		df.sort_values(['Track', 'Plane'], kind='mergesort', inplace=True)
		df.reset_index(drop=True, inplace=True)
		self._dataframe = df
		self.compute_track_pos(self._n_smooth)

	##################################################
	def _get_links(self, ref: pd.DataFrame, use_3d: bool = False) -> LinkResult:
		"""
		Calcule l’appariement des pistes entre un référentiel `ref` et `self._track_pos`,
		en renvoyant pour chaque piste de la référence le numéro de piste correspondant dans l’objet courant.

		:param ref: Tableau de référence (pistes en index ou colonne « Track ») avec X/Y[/Z].
		:param use_3d: Si True, la distance inclut Z (X,Y,Z). Sinon 2D (X,Y).
		:return: Tableau de longueur = nb de pistes dans `ref` (triées par identifiant croissant) tel que : res[i] = id_dans_courant  (ou -1 si aucune
		trouvée).
		"""
		if self._track_pos is None:
			raise AttributeError("Le fichier doit-être chargé et les positions de chaque trajectoires calculées.")

		# --- Colonnes utilisées ---
		cols = ['CentroidX(px)', 'CentroidY(px)'] + (['CentroidZ(um)'] if use_3d else [])

		# Liste ordonnée de tous les identifiants de la référence
		a = ref.loc[:, cols].to_numpy(dtype=float, copy=True)			   # (Ref, dimensions)
		b = self._track_pos.loc[:, cols].to_numpy(dtype=float, copy=True)  # (Current, dimensions)
		cur_ids = self._track_pos.index.to_numpy(copy=False)			   # (C,)
		r, c = a.shape[0], b.shape[0]
		map_pos = np.full(r, -1, dtype=int)
		map_id = np.full(r, -1, dtype=int)
		deltas = np.full((r, a.shape[1]), np.nan, dtype=float)

		if len(a) != len(b):
			print(f"{COLOR_WRN}Attention : le nombre de Trajectoires n'est pas le même entre les deux fichiers,"
				  f" l'appariement peut devenir instable.{COLOR_RESET}")
		if r == 0 or c == 0:
			print(f"{COLOR_WRN}Attention : Aucune trajectoire dnas un des fichiers.{COLOR_RESET}")
			return LinkResult(map_pos, map_id, deltas, tuple(cols))

		diff = a[:, None, :] - b[None, :, :]				  # Ajout d'un axe pour faciliter le couplage de toutes les trajectoires en une ligne
		dist = np.sqrt(np.einsum('rij,rij->ri', diff, diff))  # plus stable que (diff**2).sum(axis=2) mais équivalent
		r_idx, c_idx = linear_sum_assignment(dist)			  # Appariement Hongrois

		# Remplissage : Δ = cur - ref = -diff[r,c,:]
		for r, c in zip(r_idx, c_idx):
			map_pos[r] = c
			map_id[r] = int(cur_ids[c])
			deltas[r] = -diff[r, c, :]

		return LinkResult(map_pos, map_id, deltas, tuple(cols))


##################################################
if __name__ == "__main__":
	fm, fm2 = RegisterFileManager(), RegisterFileManager()
	fm.open(Path("Data/A/A_Pos-1_001.PT/Register.txt"))
	fm.compute_track_pos(10)
	fm2.open(Path("Data/A/A_Pos-1_002.PT/Register.txt"))
	fm2.compute_track_pos(10)
	fm2.align(fm)
	fm2.save(Path("Data/A/A_Pos-1_002.PT/Register2.txt"))
