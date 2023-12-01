""" Fichier principal de calcul du SRI """

import os

import pandas as pd

##################################################
def agenda_to_timestamp(dataframe: pd.DataFrame):
    """
    Transforme un agenda csv avec les colonnes :
     - Date (un entier allant de 1 à N),
     - Start, Début de la plage horaire (au format HH:MM)
     - End, Fin de la plage horaire (au format HH:MM)
     - State, Etat éveillé ou endormi (S ou W)
    En un tableau de même précision que l'actimètre (avec un enregistrement par minute)
    :param dataframe: Dataframe de l'agenda
    :return: Dataframe contenant l'agenda minute par minute
    """
    res = []
    dataframe = change_time(dataframe, "Start", "Start")  # Change la colonne Start pour etre en minutes allant de 0 à 1440.
    dataframe = change_time(dataframe, "End", "End")  # Change la colonne End pour etre en minutes allant  de 0 à 1440.
    for i in range(len(dataframe)):
        for t in range(dataframe.loc[i, "Start"], dataframe.loc[i, "End"] + 1):
            res.append([dataframe.iloc[i, 0], t, dataframe.iloc[i, 3]])
    return pd.DataFrame(data=res, columns=["Date", "Time", "Sleep or Awake?"])

##################################################
def change_date(dataframe: pd.DataFrame, col: str = "Date", new_col: str = "Day"):
    """
    Change la date au format (JJ/MM/AAAA) pour un jour allant de 1 à N.
    :param dataframe: dataframe à analyser.
    :param col: Colonne d'origine du jour au format (JJ/MM/AAAA) (par défaut "Date").
    :param new_col: Colonne du jour allant de 1 à N (par défaut "Day"), SI col == new_col la colonne originale sera réécrite
    :return: Le dataframe modifié
    """
    dataframe[new_col] = pd.to_datetime(dataframe[col], format='%d/%m/%Y')
    start_date = dataframe[new_col].min()
    dataframe[new_col] = (dataframe[new_col] - start_date).dt.days + 1
    return dataframe

##################################################
def change_time(dataframe: pd.DataFrame, col: str = "Time", new_col: str = "Minute"):
    """
    Change l'heure au format (HH:MM) pour son équivalent en minute depuis minuit.
    :param dataframe: Dataframe à analyser.
    :param col: Colonne d'origine de l'heure au format (HH:MM) (par défaut "Time").
    :param new_col: Colonne de l'heure allant de 0 à 1440 (par défaut "Minute"), SI col == new_col la colonne originale sera réécrite
    :return: Le dataframe modifié
    """
    dataframe[new_col] = pd.to_timedelta(dataframe[col] + ':00')
    dataframe[new_col] = (dataframe[new_col].dt.total_seconds() // 60).astype(int)
    return dataframe

##################################################
def compute_SRI(dataframe: pd.DataFrame, missing_behaviour: int = 0):
    """
    Calcul le Sleep Regularity Index (SRI) à partir d'un dataframe au format "Jour", "Minute", "État d'éveil"
    :param dataframe: Dataframe au format "Jour", "Minute", "État d'éveil" à analyser.
    :param missing_behaviour: Comportement en cas de données manquantes sur un des deux jours en test (par défaut 0)
    0 : Skip : ne prend pas en compte cette époque.
    1 : Awake : la donnée manquante est considéré comme Eveil.
    2 : Sleep : la donnée manquante est considéré comme Sommeil.
    3 : Regularity : quelles que soient les données, on considère l'époque comme régulière.
    4 : Irregularity : quelles que soient les données, on considère l'époque comme irrégulière.
    :return: Le SRI en % allant théoriquement de -100 à 100 (-100 complètement irrégulier, 0 aléatoire, 100 complètement régulier).
    """
    cols = dataframe.columns.tolist()
    n_day = dataframe[cols[0]].max()
    n_min = 1440
    res = 0
    n_epochs = 0
    for i in range(n_day-1):
        day_0 = dataframe[dataframe[cols[0]] == i]
        day_1 = dataframe[dataframe[cols[0]] == i + 1]
        for j in range(n_min):
            day_0_j = day_0[day_0[cols[1]] == j]
            day_1_j = day_1[day_1[cols[1]] == j]

            if len(day_0_j) != 0 and len(day_1_j) != 0:
                n_epochs += 1
                if day_0_j.iloc[0, 2] == day_1_j.iloc[0, 2]: res += 1
            elif missing_behaviour == 1 or missing_behaviour == 2:
                n_epochs += 1
                state = "W" if missing_behaviour == 1 else "S"
                state_0 = state if len(day_0_j) == 0 else day_0_j.iloc[0, 2]
                state_1 = state if len(day_1_j) == 0 else day_1_j.iloc[0, 2]
                if state_0 == state_1: res += 1
            elif missing_behaviour == 3:
                n_epochs += 1
                res += 1
            elif missing_behaviour == 4:
                n_epochs += 1

    return -100 + res * (200 / n_epochs)

##################################################
def process(file: str):
    """
    Préparation du fichier pour ensuite calculer les index
    :param file: Fichier à analyser
    :return: un dictionnaire contenant le dataframe et les index calculés
    """
    # Récupération du nombre de lignes inutiles
    to_skip = 0
    with open(file, 'r') as f:
        for line in f:
            if line.startswith("Date"): break
            to_skip += 1

    dataframe = pd.read_csv(file, skiprows=range(to_skip))  # Utiliser pandas pour lire le reste du fichier CSV à partir de la position actuelle
    dataframe = change_date(dataframe, "Date", "Date")      # Change la colonne Date par une colonne comptant les jours allant de 1 à N.
    if len(dataframe.columns) == 4:
        dataframe = agenda_to_timestamp(dataframe)
    else:
        dataframe = change_time(dataframe, "Time", "Time")  # Change la colonne Time pour être en minutes allant de 0 à 1440.

    return dict(Dataframe=dataframe,
                SRI=compute_SRI(dataframe[["Date", "Time", "Sleep or Awake?"]], 0))

##################################################
def main(path: str):
    """
    Fonction lançant le calcul sur tous les fichiers du dossier
    :param path: Dossier contenant les csv
    """
    if not os.path.isdir(path): raise ValueError(f"Dossier {path} inexistant")
    files = os.listdir(path)
    files = [file for file in files if file.endswith(".csv")]
    # Affiche la liste des fichiers CSV
    print(f" {len(files)} Fichiers CSV dans le dossier:")
    for file in files:
        tmp = process(os.path.join(path, file))
        print(f"Fichier \"{file}\"\t: \tSRI ({tmp['SRI']} %)")

##################################################
if __name__ == "__main__":
    main("Datas")
