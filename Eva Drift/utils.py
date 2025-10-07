""" Fonctions utilitaires """
import re
import shutil
from pathlib import Path
from typing import Dict, Optional

from colorama import Fore, Style

# Constantes
COLOR_OK = Fore.GREEN
COLOR_ERR = Fore.RED
COLOR_RESET = Style.RESET_ALL

# Type de retour : pos -> pile -> Prefixe dossier original -> chemin ou None
ColorDict = Dict[str, Optional[Path]]  # Dictionnaire de couleur
StackDict = Dict[int, ColorDict]	   # Dictionnaire de pile
FilesIndex = Dict[int, StackDict]	   # Dictionnaire de position


##################################################
def get_file_list(root: Path, name: str = "Register.txt") -> FilesIndex:
	"""
    Construit un index des fichiers `name` présents (ou manquants) dans une
    arborescence d'acquisitions structurée comme suit :
      <root>/
        A/ B/ C/ ...
          A_Pos-<X>_<YYY>.PT/
            Register.txt (optionnel)

    Règles :
    - X = numéro de position (entier > 0), YYY = numéro de pile (ex: 001, 002…).
    - Les clés de retour couvrent *toutes* les combinaisons (position, pile, lettre)
      observées dans l’arborescence : si un `Register.txt` manque, la valeur est "".
    - Tri garanti et stable : positions ↑, piles ↑, lettres A..Z.

	:param root: Dossier racine contenant les sous-dossiers A, B, C, ...
	:param name: Nom du fichier à indexer (par défaut "Register.txt").
	:return:  Dictionnaire imbriqué {position: {pile: {lettre: chemin | ""}}}. Les chemins sont absolus (str).
	"""
	if not root.is_dir(): raise NotADirectoryError(f"Racine invalide: {root}")

	# motif des dossiers : prefixe arbitraire + _Pos-X_YYY.PT
	pattern = re.compile(r"^(?P<prefix>.+)_Pos-(?P<pos>\d+)_(?P<pile>\d{3})\.PT$")

	# Collecte brute des triplets (pos, pile, lettre) et chemins de Register.txt
	# On retient l’ensemble des positions, piles, lettres vus pour compléter ensuite.
	seen_pos: set[int] = set()
	seen_stacks: set[int] = set()
	seen_prefix: set[str] = set()
	hits: dict[tuple[int, int, str], Path | None] = {}

	# Parcours des sous-dossiers de "couleurs"
	for child in (p for p in root.iterdir() if p.is_dir()):
		c_name = child.name

		# Parcours des sous-dossiers *.PT
		for sub in (p for p in child.iterdir() if p.is_dir()):
			m = pattern.match(sub.name)
			if not m: continue
			prefix, pos, stack = m.group("prefix"), int(m.group("pos")), int(m.group("pile"))
			seen_prefix.add(prefix)
			seen_pos.add(pos)
			seen_stacks.add(stack)

			register_path = sub / name
			hits[(pos, stack, prefix)] = register_path if register_path.is_file() else None

	pos_sorted, stacks_sorted, prefix_sorted = sorted(seen_pos), sorted(seen_stacks), sorted(seen_prefix)
	index: FilesIndex = {}

	for pos in pos_sorted:
		piles_dict: StackDict = {}
		for stack in stacks_sorted:
			prefix_dict: ColorDict = {}
			for prefix in prefix_sorted:
				prefix_dict[prefix] = hits.get((pos, stack, prefix), None)
			piles_dict[stack] = prefix_dict
		index[pos] = piles_dict

	return index


##################################################
def clean_file_list(index: FilesIndex) -> FilesIndex:
	"""
    Réduit l'index {position -> pile -> condition -> Path|None} en supprimant :
	les piles vides de chaque position, puis retire les positions devenues vides.
	Une pile est dite *vide* si toutes ses conditions (préfixes) ne possèdent pas de fichier valides (valent `None`).
	:param index: Dictionnaire imbriqué tel que retourné par `get_files_list`.
	:return: Nouvelle structure filtrée en conservant l’ordre d’insertion (positions, piles, conditions).
	"""
	reduced: FilesIndex = {}
	for pos, piles in index.items():
		kept_piles: StackDict = {}

		for pile_id, conds in piles.items():
			# Garde la pile si au moins une condition a un fichier (Path non-None)
			if any(p is not None for p in conds.values()): kept_piles[pile_id] = conds

		if kept_piles: reduced[pos] = kept_piles  # conserve la position si au moins une pile survit

	return reduced


##################################################
def print_file_list(index: FilesIndex) -> None:
	"""
	Affiche sous forme lisible la structure hiérarchique du dictionnaire de fichiers
	retourné par :func:`get_files`.

	Structure parcourue :
		pos → stack → condition → fichier (ou "Absent")

	Chaque entrée affiche :
		• Position et stack avec indentation claire
		• Nom de la condition (préfixe d’origine)
		• Chemin absolu ou mention "Absent"

	:param index: Dictionnaire imbriqué contenant les chemins des fichiers ou None.
	"""
	if not index:
		print("(aucune donnée)")
		return

	for pos, stacks in index.items():
		print(f"Position {pos}")
		for stack, conditions in stacks.items():
			parts = []
			for name, path in conditions.items():
				sym = f"{COLOR_OK}✓{COLOR_RESET}" if path else f"{COLOR_ERR}✗{COLOR_RESET}"
				parts.append(f"{name}({sym})")
			print(f"  Pile {stack} : {', '.join(parts)}")


##################################################
def make_backup(index: FilesIndex, suffix="old") -> bool:
	"""
    Crée une sauvegarde de chaque fichier présent dans l'index, en insérant un suffixe avant la dernière extension.
    Exemple : "Register.txt" → "Register-old.txt".

    **Remarque** :
		- Multi-extensions : seul le **dernier** suffixe est considéré (ex. "archive.tar.gz" → "archive.tar-old.gz").
		- Les métadonnées (mtime, etc.) sont conservées via `shutil.copy2`.

	:param index: Dictionnaire {position → pile → condition → Path|None}.
	:param suffix: Suffixe inséré avant la dernière extension (défaut: "-old").
	"""
	# Aplatit et déduplique tous les Paths non-None de l'index
	succes = True
	for pos in index.values():
		for stack in pos.values():
			for color in stack.values():
				if not isinstance(color, Path) or not (color.exists() and color.is_file()): continue
				dst = color.with_name(f"{color.stem}-{suffix}{color.suffix}")
				if dst == color: continue	  # Cas pathologique (suffixe vide ou nom déjà identique)
				try:
					shutil.copy2(color, dst)  # copy2 conserve au mieux les métadonnées
				except Exception:
					succes = False
					print(f"{COLOR_ERR}Erreur lors du back du fichier {color} {COLOR_RESET}")
	return succes


##################################################
if __name__ == "__main__":
	fl = get_file_list(Path("Data"))  # Création de la liste des fichiers
	print_file_list(fl)				  # Affichage "propre"
	fl = clean_file_list(fl)		  # Nettoyage de la liste des fichiers (nettoyage)
	print_file_list(fl)				  # Affichage "propre"
