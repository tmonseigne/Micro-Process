import os

import numpy as np
import pandas as pd

##################################################
def format_file(filename: str):
    # Ouvrir le fichier en tant que texte
    with open(filename, 'r') as file: lines = file.readlines()

    # Trouver l'index de la ligne contenant uniquement des tirets
    index_tirets = next((i for i, line in enumerate(lines) if line.strip() == '-------------------------------------'), None)

    # Supprimer les lignes précédentes aux tirets
    lines = lines[index_tirets + 1:]

    # Remplacer les virgules par des . et les tabulations par des virgules
    lines = [line.replace(",", ".") for line in lines]
    lines = [line.replace("\t", ",") for line in lines]

    # Enregistrer les lignes modifiées dans un nouveau fichier temporaire
    with open(filename + "tmp.csv", 'w') as file: file.writelines(lines)

    # Lire le nouveau fichier CSV correctement avec pandas
    df = pd.read_csv(filename + "tmp.csv")

    # Supprimer le fichier temporaire
    os.remove(filename + "tmp.csv")
    return df

##################################################
def convert_time(time: str):
    # Supprimer les crochets et diviser la chaîne en minutes, secondes et millisecondes
    time = time.strip('[]')
    minutes, secondes, millisecondes = map(int, time.split(':'))
    # Convertir le temps en secondes (en tant que flottant)
    temps_secondes = minutes * 60 + secondes + millisecondes / 1000
    return temps_secondes

##################################################
ids = ["101DOS_Session_29-10-2020_09H42M",     "102MAM_Session_25-11-2020_10H15M",     "103LET_SessionVexp_29-12-2020_11H38M",
       "104AUT_SessionVexp_12-01-2021_18H00M", "105MOA_SessionEXP_25-01-2021_14H33M",  "107BOL_Session_10-02-2021_10H57M",
       "109MOC_Sessionexp_19-02-2021_11H34M",  "110LAA_Session_28-04-2021_10H07M",     "111HAN_Session_19-04-2021_11H17M",
       "112 FOG_Session_28-04-2021_16H05M",    "113_Session_19-05-2021_09H43M",        "114GAL_Session_02-06-2021_10H06M",
       "115ZIL_Session_30-06-2021_10H03M",     "116CRV_Session_22-07-2021_13H20M",     "117ETR_Session_20-08-2021_12H13M",
       "201COE_Session_06-08-2020_10H22M",     "202BEM_Session_28-07-2020_10H51M",     "203CHLV2_Session_30-09-2020_13H47M",
       "204KLY_Session_07-10-2020_16H11M",     "205FOL_SessionVexp_13-01-2021_13H43M", "206GIN_Session_20-08-2021_14H13M",
       "207FM_Session_25-10-2021_16H20M",      "208FA_Session_25-10-2021_10H40M",      "209FM_Session_25-10-2021_12H05M",
       "210ML_Session_16-02-2022_14H11M",      "212MOA_Session_22-04-2022_12H12M",     "213COA_Session_05-05-2022_18H24M"]

for id in ids:
    # Ouverture du fichier Raw cognition (pour récupérer les temps des blocs)
    cognition_file = os.path.join("Datas", f"{id}_Raw cognition results.csv")
    df_cognition = format_file(cognition_file)
    # récupérer le temps à la ligne Item 61, Item 121, Item 181 (début des blocs 2, 3 et 4)
    times_str = df_cognition.loc[
        (df_cognition["X"] == "Item 61") | (df_cognition["X"] == "Item 121") | (df_cognition["X"] == "Item 181"), "Time"].to_numpy().tolist()

    times = []
    for t in times_str: times.append(convert_time(t))
    print(f"Times : {times}")

    # Ouverture du fichier Raw Behavioral ()
    behavioral_file = os.path.join("Datas", f"{id}_Raw behavioral results.csv")
    df_behavioral = format_file(behavioral_file)

    last_time = df_behavioral.iloc[-1, 0]
    bloc_times = [[[0, times[0]], [0, times[0]]], [[times[0], times[1]], [times[0], times[1]]],
                  [[times[1], times[2]], [times[1], times[2]]], [[times[2], last_time], [times[2], last_time]],
                  None, [[0, times[0]], [times[1], times[2]]], [[times[0], times[1]], [times[2], last_time]]]

    rmss = []
    cols_types = ["head position", "head rotation", "feet position", "feet rotation"]
    for t in bloc_times:
        # Récupération des temps
        mask = pd.Series(np.ones(len(df_behavioral), dtype=bool)) if t is None else (df_behavioral["Time"].between(t[0][0], t[0][1])) | (
                df_behavioral["Time"].between(t[1][0], t[1][1]))
        df_filtered = df_behavioral[mask]
        bloc_rms = []
        for cols in cols_types:
            part = df_filtered.filter(like=cols).diff()  # ON a maintenant les différences entre chaque lignes
            bloc_rms.append(np.sqrt(np.nanmean(np.sum(np.square(part.to_numpy()), axis=1))))
        rmss.append(bloc_rms)

    rmss = np.array(rmss).T

    df_res = pd.DataFrame(rmss, columns=["Bloc 1", "Bloc 2", "Bloc 3", "Bloc 4", "Blocs (1, 2, 3, 4)",
                                         "Distractorless Blocks (1, 3)", "Distractors-Containing Blocks (2, 4)"],
                          index=["Head Position RMS", "Head Rotation RMS", "Feet Position RMS", "Feet Rotation RMS"])

    df_res.index.name = "Features"

    df_res.to_csv(os.path.join("Datas", f"{id}_Report.csv"), sep="\t")
