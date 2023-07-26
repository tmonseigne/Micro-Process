""" Fonctions Utiles """

import os
import glob
import numpy as np
import pandas as pd
import scipy
import seaborn as sns
import matplotlib.pyplot as plt

##################################################
def find_files(path: str, name: str = "") -> list[str]:
    """
    Recherche des fichiers dans le dossier et ses sous-dossiers qui s'appellent `name`.
    :param path: Le répertoire de base.
    :param name: Le fichier a chercher.
    :return: Une liste de chemins de fichiers.
    """
    res = []
    for root, _, files in os.walk(path):
        for file in files:
            if name != "" and file.endswith(name):
                res.append(os.path.join(root, file))

    res.sort()
    return res

##################################################
def get_stats(dataframe: pd.DataFrame):
    return [len(dataframe)] + dataframe.mean().tolist()

##################################################
def get_histogramms(axes: list[plt.axes], dataframe: pd.DataFrame, electrods):
    df = dataframe.copy()
    # Arrondir à l'unité la colonne "Frequency" dans le DataFrame resultat
    x = range(11, 17)
    bins = [x[i] - 0.5 for i in range(len(x))] + [x[-1] + 0.5]  # Définir les bords des barres

    for i in range(len(electrods)):  # Pour chaque electrode
        axes[i].clear()
        part = df.loc[df['Electrod'] == i, "Frequency"].to_numpy()
        axes[i].set_title(electrods[i])
        sns.histplot(part, bins=bins, ax=axes[i], kde=False)
        # Je veux un histogramme pour une barre à 11, 12,13,14,15,16


