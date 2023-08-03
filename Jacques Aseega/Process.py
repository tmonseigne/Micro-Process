""" Récupération des informations des fichiers Matlab """
# Necessite Python 3.8 ou supérieur `pip install pandas numpy pyplot seaborn openpyxl`

import os

import matplotlib.pyplot as plt
import pandas as pd

from libs.utils import find_files, get_histogramms, get_stats

data_path = os.path.join("Datas", "Spindles")
electrodes_used = ["C3", "C4", "F3", "F4"]
# file = os.path.join(data_path,"")

##### Fichiers, Nom de Colonnes et constantes
filenames = find_files(data_path, " Spindles.csv")
cycle_cols = ["Sujet", "Cycle", "Début", "Durée", "Fin"]
columns = ["Position", "Duration", "Power", "Frequency", "Frequential Instability",
           "Frequential Purity", "Temporal Instability", "Maximum Amplitude", "Electrod", "Cycle"]

stat_cols = ["Number"] + columns[1:-2]
res_cols = ["Subject", "Cycle", "Electrod"] + ["Low Freq " + c for c in stat_cols] + ["High Freq " + c for c in stat_cols]
cut_freq = 13
None_Line = [None] * len(res_cols)
print(None_Line)

##### Variables utiles
res = pd.DataFrame(columns=res_cols)
stats = []
fig, axes = plt.subplots(2, 2, figsize=(16, 9))
axes = axes.ravel()

##### Parcours des fichiers
cycles_df = pd.read_csv(os.path.join("Datas", "Cycles.csv"), header=None, names=cycle_cols)  # Colonnes : Sujet, Cycle, Début, Durée, Fin

for f in filenames:
    df = pd.read_csv(f, header=None, names=columns)
    df = df.apply(pd.to_numeric, errors='coerce')
    tmp = os.path.basename(f)  # Obtient le nom du fichier avec l'extension (par exemple, "sujet1 Spindles.csv")
    subject = tmp.replace(" Spindles.csv", "")  # Supprime le préfixe " Spindles.csv" pour obtenir le nom du sujet (par exemple, "sujet1")
    subject_number = int(subject[3:])  # Récupération du numéro du sujet
    print(f"Sujet {subject_number}")

    tmp_line = None_Line.copy()
    tmp_line[0] = subject
    stats.append(pd.DataFrame([tmp_line], columns=res_cols))

    # Récupération des cycles du sujet
    subject_cycles = cycles_df[cycles_df["Sujet"] == subject_number]

    # Calcul des Stats
    print(f"    Calcul des stats")
    for c in range(len(subject_cycles)):
        tmp_line = None_Line.copy()
        if c == 0:
            cycle_df = df
            tmp_line[1] = "Nuit Complete"
        else:
            mask = subject_cycles["Cycle"] == c
            start = subject_cycles.loc[mask, "Début"].to_numpy()[0]
            end = subject_cycles.loc[mask, "Fin"].to_numpy()[0]
            cycle_df = df[(df['Position'] >= start) & (df['Position'] <= end)]
            tmp_line[1] = f"Cycle {c}"

        stats.append(pd.DataFrame([tmp_line], columns=res_cols))
        for i in range(4):  # Pour chaque electrode
            s = [None, None, electrodes_used[i]]
            mask_1 = (cycle_df['Electrod'] == i) & (cycle_df['Frequency'] <= cut_freq)
            s.extend(get_stats(cycle_df.loc[mask_1, columns[1:-2]]))
            mask_2 = (cycle_df['Electrod'] == i) & (cycle_df['Frequency'] >= cut_freq)
            s.extend(get_stats(cycle_df.loc[mask_2, columns[1:-2]]))
            stats.append(pd.DataFrame([s], columns=res_cols))

    stats.append(pd.DataFrame([None_Line], columns=res_cols))

    print(f"    Calcul des Histogrammes")
    get_histogramms(axes, df, electrodes_used)
    fig.suptitle(f"Fuseaux Histogrammes Sujet {subject}", fontsize=16)
    plt.savefig(os.path.join(data_path, f"Fuseaux Histogrammes Sujet {subject}.png"), bbox_inches="tight")

res = pd.concat(stats)
res.to_csv(os.path.join(data_path, "Stats.csv"), index=False)
res.to_excel(os.path.join(data_path, "Stats.xlsx"), index=False)

print("Fini")
