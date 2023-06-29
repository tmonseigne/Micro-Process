""" Récupération des informations de l'excel BaMaRa """
# Necessite Python 3.8 ou supérieur `pip install numpy pandas openpyxl`

import numpy as np
import pandas as pd

file = "Extract.xlsx"             # Fichier d'origine
output_file = "BaMaRa.xlsx"       # Fichier contenant les informations utiles
output_stats_file = "Stats.xlsx"  # Fichier de Stats

sheets_name = [0, 1, 2, 3]  # Feuilles d'intérêt du fichier BaMaRa
# Colonnes du fichier BaMaRa pour les 4 feuilles sélectionnées
columns = [["ID BaMaRa", "Non malade", "Nom de naissance", "Prénom", "Date de naissance"],  # Données administratives
           ["ID BaMaRa", "Date de la dernière activité"],                                   # Prises en charge
           ["ID BaMaRa", "première activité le", "Fait le"],                                # Activités
           ["ID BaMaRa", "Statut", "Maladie rare (Orphanet)"]]                              # Diagnostics

# Colonnes du fichier de concaténation
final_columns = ["ID", "Nom", "Prénom", "Date de naissance", "Première activité", "Dernière activité", "Statut", "Diagnostic", "Malade"]

years_selection = range(2019, 2024)                   # Années d'intérêt
stats_type = ["File Active", "Activité", "Nouveaux"]  # Type de catégories
maladies = ["Narcolepsie de type 1", "Narcolepsie de type 2", "Narcolepsie sans cataplexie", "Hypersomnie idiopathique",
            "Syndrome de Kleine-Levin", "Indéterminé/Non renseigné"]  # Maladies identifiées

# Lignes du fichier de Stats
stats_index = []
for stat in stats_type:
    stats_index.append(stat)
    for maladie in maladies + ["Malade", "Non malade", "Total"]:
        stats_index.append(stat + " - " + maladie)

##################################################
# Ouverture et sélection des informations
print(f"Ouverture du fichier : {file}")
dataframes = pd.read_excel(file, sheet_name=sheets_name)                                # Ouverture en un dictionnaire de dataframes (1 par feuille de l'excel)
for i in range(4): dataframes[i] = dataframes[i][columns[i]]                            # Sélection des colonnes
dataframes[3].loc[dataframes[3]["Maladie rare (Orphanet)"] == "Narcolepsie-cataplexie", "Maladie rare (Orphanet)"] = "Narcolepsie de type 1"
#dataframes[3].loc[dataframes[3]["Maladie rare (Orphanet)"] == "Narcolepsie sans cataplexie", "Maladie rare (Orphanet)"] = "Narcolepsie de type 2"
mask = ~dataframes[3]["Statut"].isna()                                                  # Ceux qui ont un statut
dataframes[3].loc[mask, "Maladie rare (Orphanet)"] = dataframes[3].loc[mask, "Maladie rare (Orphanet)"].fillna("Indéterminé/Non renseigné")
dataframes[3] = dataframes[3][dataframes[3]["Maladie rare (Orphanet)"].isin(maladies)]  # Selection des diagnostics

##################################################
# Récupération et Concaténation des informations
final_df = pd.DataFrame(columns=final_columns)  # Création du dataframe final

final_df[["ID", "Malade", "Nom", "Prénom", "Date de naissance"]] = dataframes[0][columns[0]]  # Récupération des infos administratives
ids = final_df["ID"].unique().tolist()  # Récupération des ID
for id_ in ids:
    # Prises en charge pour la derniere activité
    tmp = dataframes[1].loc[dataframes[1]["ID BaMaRa"] == id_, "Date de la dernière activité"].dropna().to_numpy()
    if len(tmp) == 0:
        print(f"Erreur pour l'identifiant {id_}, pas de Date de dernière activité.")
        final_df = final_df.drop(final_df[final_df["ID"] == id_].index)
        continue
    elif len(tmp) > 1: print(f"Erreur pour l'identifiant {id_}, plusieurs de Date de dernière activité.")
    else:    final_df.loc[final_df["ID"] == id_, "Dernière activité"] = tmp[0]

    # Activités pour la première activité et le compte par an.
    tmp = dataframes[2].loc[dataframes[2]["ID BaMaRa"] == id_, "première activité le"].dropna().to_numpy()
    if len(tmp) != 0: final_df.loc[final_df["ID"] == id_, "Première activité"] = tmp[0]
    tmp = dataframes[2].loc[dataframes[2]["ID BaMaRa"] == id_, "Fait le"].dropna().to_numpy()
    if len(tmp) != 0:
        years = np.array([int(date[-4:]) for date in tmp])
        for y in years_selection: final_df.loc[final_df["ID"] == id_, f"Activités {y}"] = np.sum(years == y)

    # Diagnostics pour le Nom des maladies et leur statut
    tmp = dataframes[3].loc[dataframes[3]["ID BaMaRa"] == id_, ["Statut", "Maladie rare (Orphanet)"]].dropna().to_numpy()
    if len(tmp) == 0: continue
    if len(tmp) > 1: print(f"Erreur pour l'identifiant {id_}, plusieurs Statut et/ou Maladie Rare : \n{tmp}")
    final_df.loc[final_df["ID"] == id_, ["Statut", "Diagnostic"]] = tmp[0]

# Uniformisation de la casse
final_df["Nom"] = final_df["Nom"].str.title()
final_df["Prénom"] = final_df["Prénom"].str.title()
final_df["Malade"] = final_df["Malade"].str.title()
final_df["Statut"] = final_df["Statut"].str.title()

# Enregistrement
final_df = final_df.sort_values(by="Nom")
final_df.to_excel(output_file, index=False)
final_df.to_csv(output_file + ".csv", index=False)

##################################################
# Calcul du fichier de stat
stats_df = pd.DataFrame(0, columns=years_selection, index=stats_index)  # Création du dataframe de Stat rempli de 0.

for y in years_selection:
    for m in maladies + ["Non malade"]:
        filt_df = final_df.copy()
        mask = filt_df["Statut"].isna()     # Non malades (sans diagnostic)
        if m != "Non malade":               # Malades (avec diagnostic)
            if m == "Indéterminé/Non renseigné": mask = ~mask & ((filt_df["Statut"] == "Indéterminé") | (filt_df["Diagnostic"] == m))
            else:                                mask = ~mask & ((filt_df["Statut"] != "Indéterminé") & (filt_df["Diagnostic"] == m))
        filt_df = filt_df[mask]                         # Filtre sur Malade / non malade
        tmp = filt_df[filt_df[f"Activités {y}"] != 0]   # Activité sur l'année
        print(f"Année : {y}, maladie : {m}, filtre len : {len(tmp)}")
        if len(filt_df) == 0: continue

        # "File Active" (au moins 1 consultation dans l'année)
        stats_df.loc[stats_type[0] + " - " + m, y] = len(tmp)
        # "Consultation" (Nombre de consultations dans l'année)
        stats_df.loc[stats_type[1] + " - " + m, y] = filt_df.loc[:, f"Activités {y}"].sum()
        # "Nouveaux" (Première consultation dans l'année)
        tmp = filt_df.loc[:, "Première activité"].dropna().to_numpy()
        first_year = np.array([int(date[-4:]) for date in tmp])
        stats_df.loc[stats_type[2] + " - " + m, y] = np.sum(first_year == y)

# Aménagement
for s in stats_type:
    stats_df.loc[s, :] = np.nan
    for y in years_selection:
        Total_malade = 0
        for m in maladies:
            Total_malade += stats_df.loc[s + " - " + m, y]
        stats_df.loc[s + " - Malade", y] = Total_malade
        stats_df.loc[s + " - Total", y] = stats_df.loc[s + " - Malade", y] + stats_df.loc[s + " - Non malade", y]

stats_df = stats_df.astype('Int64')

# Enregistrement
stats_df.index.name = "Catégorie"  # Ajout d'un titre aux index
stats_df.to_excel(output_stats_file)
stats_df.to_csv(output_stats_file + ".csv")

##################################################
# Graphiques ?
