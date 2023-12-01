""" Fichier principal de calcul du SRI """

import os

import pandas as pd

##################################################
def change_date(dataframe: pd.DataFrame):
    dataframe["Jour"] = pd.to_datetime(dataframe["Date"], format='%d/%m/%Y')
    start_date = dataframe["Jour"].min()
    dataframe['Jour'] = (dataframe['Jour'] - start_date).dt.days + 1
    return dataframe

##################################################
def change_time(dataframe: pd.DataFrame):
    dataframe['Minute'] = pd.to_timedelta(dataframe['Time'] + ':00')
    dataframe['Minute'] = (dataframe['Minute'].dt.total_seconds() // 60).astype(int)
    return dataframe

##################################################
def compute_SRI(dataframe: pd.DataFrame, missing_behaviour: int = 0):
    """
    Dataframe au format "Jour", "Minute", "Eveil"
    :param dataframe: Dataframe contenant les données
    :param missing_behaviour: Comportement en cas de données manquantes sur un des deux jours en test (par défaut 0)
    0 : Skip, ne prend pas en compte cette époque
    1 : Awake, la donnée manquante est considéré comme Eveil
    2 : Sleep, la donnée manquante est considéré comme Sommeil
    3 : Regularity, quelque soit les données, on considère l'époque comme régulière
    4 : Irregularity, quelque soit les données, on considère l'époque comme irrégulière
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
def process(filename: str):
    dataframe = pd.read_csv(filename)
    dataframe = change_date(dataframe)
    dataframe = change_time(dataframe)
    return dict(
            File=filename,
            Dataframe=dataframe,
            SRI=compute_SRI(dataframe[["Jour", "Minute", "Sleep or Awake?"]]))

##################################################
path = "Datas"
file = "TEST.csv"
print(process(os.path.join(path, file)))
