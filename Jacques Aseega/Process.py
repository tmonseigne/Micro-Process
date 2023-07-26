""" Récupération des informations des fichiers Matlab """
# Necessite Python 3.8 ou supérieur `pip install scipy numpy pandas`

import os
import glob

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import seaborn as sns
from libs.utils import find_files, get_histogramms, get_stats

data_path = os.path.join("Datas", "Spindles")
electrodes_used = ["C3", "C4", "F3", "F4"]
#file = os.path.join(data_path,"")

##### Fichiers, Nom de Colonnes et constantes
filenames = find_files(data_path, " Spindles.csv")
columns = ["Position", "Duration", "Power", "Frequency", "Frequential Instability",
           "Frequential Purity", "Temporal Instability", "Maximum Amplitude", "Electrod", "Cycle"]

stat_cols = ["Number"] + columns[1:-2]
res_cols = ["Subject", "Electrod"] + ["Low Freq " + c for c in stat_cols] + ["High Freq " + c for c in stat_cols]
cut_freq = 13

##### Variables utiles
res = pd.DataFrame(columns=res_cols)
stats = []
fig, axes = plt.subplots(2, 2, figsize=(16, 9))
axes = axes.ravel()

##### Parcours des fichiers
for f in filenames:
    df = pd.read_csv(f, header=None, names=columns)
    df = df.apply(pd.to_numeric, errors='coerce')
    tmp = os.path.basename(f)                   # Obtient le nom du fichier avec l'extension (par exemple, "sujet1 Spindles.csv")
    subject = tmp.replace(" Spindles.csv", "")  # Supprime le préfixe " Spindles.csv" pour obtenir le nom du sujet (par exemple, "sujet1")
    print(f"Sujet {subject}")

    print(f"    Calcul des stats")
    for i in range(4):  # Pour chaque electrode
        s = [subject, electrodes_used[i]]
        mask_1 = (df['Electrod'] == i) & (df['Frequency'] <= cut_freq)
        s.extend(get_stats(df.loc[mask_1, columns[1:-2]]))
        mask_2 = (df['Electrod'] == i) & (df['Frequency'] >= cut_freq)
        s.extend(get_stats(df.loc[mask_2, columns[1:-2]]))
        stats.append(pd.DataFrame([s], columns=res_cols))

    print(f"    Calcul des Histogrammes")
    get_histogramms(axes, df, electrodes_used)
    fig.suptitle(f"Fuseaux Histogrammes Sujet {subject}", fontsize=16)
    plt.savefig(os.path.join(data_path, f"Fuseaux Histogrammes Sujet {subject}.png"), bbox_inches="tight")

res = pd.concat(stats)
res.to_csv(os.path.join(data_path, "Stats.csv"), index=False)

