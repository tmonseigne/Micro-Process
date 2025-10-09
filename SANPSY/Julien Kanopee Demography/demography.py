""" Fichier principal de calcul demographique pour Kanopee """

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

file = "sommeil.csv"
output_path = "Output"
limit_age = [10, 90]
n_studies = 4
n_csp = 9

stats_columns = ["N", "Age mean", "Age std", "Sex 1", "Sex 2"]
stats_columns += [f"Studies {i}" for i in range(n_studies)]
stats_columns += [f"CSP {i}" for i in range(n_csp)]
departments = list(range(1, 96)) + [971, 972, 973, 974, 976]

##################################################
def get_lasts_periods(dataframe):
    """
    Séparation du dataframe en sous dataframe par période.
    :param dataframe: Dataframe de sommeil
    :return: Un dictionnaire avec des dataframes par periode (total, dernière année, dernier mois, dernière semaine)
    """
    today = datetime.today()
    year_dataframe = dataframe[dataframe['Date'] >= today - pd.DateOffset(years=1)]
    month_dataframe = dataframe[dataframe['Date'] >= today - pd.DateOffset(months=1)]
    week_dataframe = dataframe[dataframe['Date'] >= today - pd.DateOffset(days=7)]
    return {"Total":      dataframe,
            "Last Year":  year_dataframe,
            "Last Month": month_dataframe,
            "last Week":  week_dataframe}

##################################################
def create_evolutions(dataframe, axes, month=True):
    """
    Créé les courbes d'évolutions
    :param dataframe: Dataframe de stats
    :param axes: Axes à remplir
    :param month: Paramètre permettant de définir si on est sur un dataframe mois par mois ou semaine par semaine
    """
    if month: dataframe["Date"] = dataframe["Month"].astype(str) + '/' + dataframe["Year"].astype(str)
    for i in range(len(axes)):
        axes[i].clear()
        axes[i].tick_params(axis='x', rotation=45)

    # Number of participants
    axes[0].plot(dataframe["Date"], dataframe["N"])
    axes[0].set_ylabel("Number of participants")

    # Age
    axes[1].plot(dataframe["Date"], dataframe["Age mean"])
    axes[1].set_ylabel("Age mean")

    # Sex repartition
    axes[2].plot(dataframe["Date"], dataframe[stats_columns[3]], label=stats_columns[3])
    axes[2].plot(dataframe["Date"], dataframe[stats_columns[4]], label=stats_columns[4])
    axes[2].set_ylabel("Sex repartition")
    axes[2].legend(loc='upper right')

    # Studies repartition
    for i in range(n_studies): axes[3].plot(dataframe["Date"], dataframe[f"Studies {i}"], label=f"Studies {i}")
    axes[3].set_ylabel("Studies repartition")
    axes[3].legend(loc='upper right')

    # CSP repartition
    for i in range(n_studies): axes[4].plot(dataframe["Date"], dataframe[f"CSP {i}"], label=f"CSP {i}")
    axes[4].set_ylabel("CSP repartition")
    axes[4].set_xlabel("Date")
    axes[4].legend(loc='upper right')

##################################################
def get_months_stats(dataframe):
    """
    Récupère les stats du Dataframe mois par mois.
    :param dataframe: Dataframe de sommeil
    :return: Dataframe avec les stats
    """
    res = []
    res_dep = []
    for year, year_group in dataframe.groupby(dataframe["Date"].dt.year):
        for month, month_group in year_group.groupby(dataframe["Date"].dt.month):
            res.append([year, month] + get_dataframe_stats(month_group))
            res_dep.append([year, month, len(month_group)] + get_departments_row(month_group))

    res = pd.DataFrame(data=res, columns=["Year", "Month"] + stats_columns)
    res_dep = pd.DataFrame(data=res_dep, columns=["Year", "Month", "N"] + departments)
    return res, res_dep

##################################################
def get_weeks_stats(dataframe):
    """
    Récupère les stats du Dataframe semaine par semaine.
    :param dataframe: Dataframe de sommeil
    :return: Dataframe avec les stats
    """
    res = []
    res_dep = []

    # Déterminer la première et la dernière date dans votre DataFrame
    start = dataframe['Date'].min()
    end = dataframe['Date'].max()

    # Ajuster la date de début au lundi précédent si nécessaire
    if start.weekday() != 0:  # Si la date de début n'est pas déjà un lundi (0 représente le lundi)
        start = start - pd.DateOffset(days=start.weekday() + 7)

    # Itérer semaine par semaine
    current_date = start
    while current_date <= end:
        week = dataframe[(current_date <= dataframe["Date"]) & (dataframe["Date"] < current_date + pd.DateOffset(7))]
        res.append([current_date] + get_dataframe_stats(week))
        res_dep.append([current_date, len(week)] + get_departments_row(week))
        current_date += pd.DateOffset(7)

    res = pd.DataFrame(data=res, columns=["Date"] + stats_columns)
    res_dep = pd.DataFrame(data=res_dep, columns=["Date", "N"] + departments)
    return res, res_dep

##################################################
def get_departments_row(dataframe):
    """
    Récupère les stats departement par département.
    :param dataframe: Dataframe de sommeil
    :return: Dataframe avec le nombre de nouveau venu par département
    """
    res = np.zeros(len(departments)).astype(int).tolist()
    for i in range(len(departments)):
        res[i] = (dataframe["Departement"] == departments[i]).sum()
    return res

##################################################
def get_departments(dataframes):
    """
    Récupère les stats departement par département en séparant par total, dernière année, dernier mois, dernière semaine.
    :param dataframes: Dataframes de sommeil (dictionnaire de partie de dataframe)
    :return: Dataframe avec le nombre de nouveau venu par département et par période
    """
    res = []
    for key, value in dataframes.items():
        res.append([key, len(value)] + get_departments_row(value))
    return pd.DataFrame(data=res, columns=["Period", "N"] + departments)

##################################################
def get_dataframe_stats(dataframe):
    """
    Récupère les stats du Dataframe.
    :param dataframe: Dataframe de sommeil
    :return: Dataframe avec les stats
    """
    if len(dataframe) == 0: return np.zeros(len(stats_columns)).astype(int).tolist()

    ratio = 100.0 / len(dataframe)

    res = [len(dataframe),
           np.nanmean(dataframe.loc[(limit_age[0] <= dataframe["Age"]) & (dataframe["Age"] <= limit_age[1]), "Age"]).round(2),
           np.nanstd(dataframe.loc[(limit_age[0] <= dataframe["Age"]) & (dataframe["Age"] <= limit_age[1]), "Age"]).round(2),
           np.round(ratio * (dataframe["Sex"] == 1).sum(), 2),
           np.round(ratio * (dataframe["Sex"] == 2).sum(), 2)]
    for i in range(n_studies): res.append(np.round(ratio * (dataframe["Studies"] == i).sum(), 2))
    for i in range(n_csp):     res.append(np.round(ratio * (dataframe["Csp"] == i).sum(), 2))

    return res

##################################################
def get_stats(dataframe):
    """
    Récupère les stats du Dataframe en séparant par total, dernière année, dernier mois, dernière semaine.
    :param dataframe: Dataframe de sommeil
    :return: Dataframe avec les stats
    """
    res = []
    dataframes = get_lasts_periods(dataframe)
    for key, value in dataframes.items():
        res.append([key] + get_dataframe_stats(value))
    return pd.DataFrame(data=res, columns=["Period"] + stats_columns), get_departments(dataframes)

##################################################
def main():
    """ Fonction lançant le calcul """
    dataframe = pd.read_csv(file, usecols=range(11), sep=";")  # Utiliser pandas pour lire le fichier sommeil
    dataframe.columns = dataframe.columns.str.lstrip()
    # Vérification de l'existance des principales colonnes utilisées
    for col in ["Id", "Date inscription", "derniere_donnee", "nb_jours", "Age", "Sex", "Studies", "Csp", "Postal"]:
        if col not in dataframe.columns:
            print(f"La colonne '{col}' n'existe pas dans le DataFrame.")

    # Transformation de la date
    dataframe['Date'] = pd.to_datetime(dataframe['Date inscription'], format='%d/%m/%Y')
    # Transformation du code postal
    dataframe["Departement"] = (dataframe["Postal"] / 1000)
    dataframe["Departement"].fillna(-1, inplace=True)
    dataframe["Departement"] = dataframe["Departement"].astype(int)

    # Récupération des stats totales
    stats_df, departments_df = get_stats(dataframe)
    stats_df.to_csv(os.path.join(output_path, "total stats.csv"), index=False)
    departments_df.to_csv(os.path.join(output_path, "total departments.csv"), index=False)

    # Récupération mois par mois
    month_df, month_dep_df = get_months_stats(dataframe)
    month_df.to_csv(os.path.join(output_path, "month stats.csv"), index=False)
    month_dep_df.to_csv(os.path.join(output_path, "month departments.csv"), index=False)

    # Récupération semaine par semaine
    week_df, week_dep_df = get_weeks_stats(dataframe)
    week_df.to_csv(os.path.join(output_path, "week stats.csv"), index=False)
    week_dep_df.to_csv(os.path.join(output_path, "week departments.csv"), index=False)

    # Graphiques
    fig, axes = plt.subplots(5, 1, figsize=(16, 10), dpi=200)
    axes = axes.ravel()
    create_evolutions(month_df, axes)
    fig.tight_layout()
    fig.savefig(os.path.join(output_path, f"Evolution by month.png"), bbox_inches="tight")
    create_evolutions(week_df, axes, False)
    fig.tight_layout()
    fig.savefig(os.path.join(output_path, f"Evolution by week.png"), bbox_inches="tight")

##################################################
if __name__ == "__main__":
    os.makedirs(output_path, exist_ok=True)  # Créer le dossier de résultat (la première fois, il n'existe pas)
    main()
