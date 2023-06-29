""" Combine les csv """

import glob

import pandas as pd

filename = "all_kanopee"

# Utilisation de glob pour récupérer les fichiers
file_pattern = filename + "_[0-9]*.csv"
file_list = glob.glob(file_pattern)

dataframes = []
for file in file_list:
    print(f"Ouverture du fichier : {file}")
    dataframes.append(pd.read_csv(file))
    print(f"Nombre de colonnes : {len(dataframes[-1].columns)}")

print(f"Concatenation des fichiers")
combined_df = pd.concat(dataframes, ignore_index=True, sort=False)
print(f"Nombre de colonnes : {len(combined_df.columns)}")
combined_df.to_csv(f"{filename}.csv", index=False)
