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

stats_columns = ["N", "Age", "Sex 1", "Sex 2"]
stats_columns += [f"Studies {i}" for i in range(n_studies)]
stats_columns += [f"CSP {i}" for i in range(n_csp)]
departments = list(range(1, 96)) + [971, 972, 973, 974, 976]

##################################################
def create_evolutions(dataframe, axes, month=True):
    if month: dataframe["Date"] = dataframe["Month"].astype(str) + '/' + dataframe["Year"].astype(str)
    for i in range(len(axes)):
        axes[i].clear()
        axes[i].tick_params(axis='x', rotation=45)

    # Number of participants
    axes[0].plot(dataframe["Date"], dataframe["N"])
    axes[0].set_ylabel("Number of participants")

    # Age
    axes[1].plot(dataframe["Date"], dataframe["Age"])
    axes[1].set_ylabel("Age")

    # Sex repartition
    axes[2].plot(dataframe["Date"], dataframe[stats_columns[2]], label=stats_columns[2])
    axes[2].plot(dataframe["Date"], dataframe[stats_columns[3]], label=stats_columns[3])
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
    res = np.zeros(len(departments)).astype(int).tolist()
    for i in range(len(departments)):
        res[i] = (dataframe["Departement"] == departments[i]).sum()
    return res

##################################################
def get_departments(dataframe, month_dataframe, week_dataframe):
    res = [["Total", len(dataframe)] + get_departments_row(dataframe),
           ["Last Month", len(month_dataframe)] + get_departments_row(month_dataframe),
           ["Last Week", len(week_dataframe)] + get_departments_row(week_dataframe)]
    return pd.DataFrame(data=res, columns=["Period", "N"] + departments)

##################################################
def get_dataframe_stats(dataframe):
    if len(dataframe) == 0: return np.zeros(4 + n_studies + n_csp).astype(int).tolist()

    res = [len(dataframe),
           np.nanmean(dataframe.loc[(limit_age[0] <= dataframe["Age"]) & (dataframe["Age"] <= limit_age[1]), "Age"]).round(2),
           (dataframe["Sex"] == 1).sum(), (dataframe["Sex"] == 2).sum()]
    for i in range(n_studies): res.append((dataframe["Studies"] == i).sum())
    for i in range(n_csp):     res.append((dataframe["Csp"] == i).sum())

    return res

##################################################
def get_stats(dataframe, month_dataframe, week_dataframe):
    res = [["Total"] + get_dataframe_stats(dataframe),
           ["Last Month"] + get_dataframe_stats(month_dataframe),
           ["Last Week"] + get_dataframe_stats(week_dataframe)]
    return pd.DataFrame(data=res, columns=["Period"] + stats_columns), get_departments(dataframe, month_dataframe, week_dataframe)

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
    # Séparation en 3 groupes (original, dernier mois, derniere semaine)
    today = datetime.today()
    last_month = today - pd.DateOffset(months=1)
    last_week = today - pd.DateOffset(days=7)
    month_dataframe = dataframe[dataframe['Date'] >= last_month]
    week_dataframe = dataframe[dataframe['Date'] >= last_week]

    # Récupération des stats totales
    stats_df, departments_df = get_stats(dataframe, month_dataframe, week_dataframe)
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
