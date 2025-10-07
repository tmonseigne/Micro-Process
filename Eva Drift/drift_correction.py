""" Correction du Drift mécanique entre pluseiurs trajectoires de DNA Paint """
# Necessite Python 3.8 ou supérieur `pip install colorama numpy pandas scipy`

import sys
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style

from RegisterFileManager import RegisterFileManager
from utils import clean_file_list, get_file_list, make_backup, print_file_list

# Constantes
COLOR_OK = Fore.GREEN
COLOR_ERR = Fore.RED
COLOR_WRN = Fore.YELLOW
COLOR_RESET = Style.RESET_ALL

####################################################
#################### Paramètres ####################
####################################################
# Chemin vers le dossier à analyser
# Attention, il est parfois préférable de simplifier les chemins (exemple : C:\mon_dossier)
# car des chemins trop long peuvent dans certains cas provoquer des problèmes (après un certains nombre de caractères, il abandonne).
# Je pense également qu'un chemin vers le serveur peut poser des problèmes de droits ou autre lors de l'écriture du fichier ou même des backups
# ROOT = Path("M:\everyone\_Transferts\Transfert Eva\250924_neuron_test#1")
ROOT = Path("Data")

# Mettre à True si une erreur lors du backup des fichiers est tolérable (vous avez une copie ailleurs ou vous faites totalement confiance au process)
ALLOW_BACKUP_FAIL = False

# Nombre de point à moyenner pour définir la position initiale d'une trajectoire.
N_SMOOTH = 5

# Si à `True` et si des fichiers ont des trajectoires supplémentaires par rapport à la première couleur, supprime ces trajectoire en trop
REMOVE_UNLINK_TRACK = False

# Définit si le Z est pris en compte lors de l'alignement
# ATTENTION : les échelles peuvent fausser le résultat.
# Exemple "éxagéré" :
# Track 1 Position de départ (5, 5, -100), Track à lier Position de départ (5, 5, -90) mais Track "parasite" (7,7,-100)
# Avec USE_3D la track parasite sera liée, à False, ce sera la bonne. Mais le Z ne s'alignera pas
USE_3D = True

#################################################
#################### Process ####################
#################################################
# Récupération et classement des fichiers
file_list = clean_file_list(get_file_list(ROOT))
print(f"\n**************************************************")
print("Liste des dossiers et fichiers détectés : ")
print_file_list(file_list)

# Backup des fichiers
backup_suffix = datetime.now().strftime("%Y%d%m_%H%M%S")
backup_try = make_backup(file_list, backup_suffix)
if not backup_try and not ALLOW_BACKUP_FAIL:
	print("Erreur lors du Backup, arrêt du script")
	sys.exit(2)  # code de retour ≠ 0 pour échouer en CI/build

print(f"\n**************************************************")
print(f"Backup des fichiers effectués sous {COLOR_OK}*-{backup_suffix}{COLOR_RESET}")

# Ouverture et alignement des fichiers Registers
print(f"\n**************************************************")
print(f"Process en cours : ")
for pos, stacks in file_list.items():
	print(f"\nPosition {pos}")
	for stack, colors in stacks.items():
		print(f"  Pile {stack}")
		managers: list[RegisterFileManager] = []
		c_name = list(colors.keys())
		for color, path in colors.items():
			status = f"{COLOR_OK}Present{COLOR_RESET}" if path else f"{COLOR_ERR}Absent{COLOR_RESET}"
			line = f"    {color:<15} : {status}"
			if path is None: continue
			rfm = RegisterFileManager()
			rfm.open(path)
			rfm.compute_track_pos(N_SMOOTH)
			managers.append(rfm)
		# Maintenant checker avec le premier manager
		print(f"    Alignement de la Pile {stack}...")
		for i in range(1, len(managers)):
			managers[i].align(managers[0], REMOVE_UNLINK_TRACK, USE_3D)
			managers[i].save()  # Ecraser le resultat original
			print(f"      Couleur {c_name[i]} aligné avec {c_name[0]}.")

print(f"\n{COLOR_OK}Fini !{COLOR_RESET}")
