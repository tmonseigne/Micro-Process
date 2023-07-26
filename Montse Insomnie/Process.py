""" Récupération des informations des fichiers Matlab """
# Necessite Python 3.8 ou supérieur `pip install scipy numpy pandas`

import os

import pandas as pd

data_path = "Datas"
filename = "mkanopee_20_07_23"
file = os.path.join(data_path, f"{filename}.csv")

##### Etape 1 ouverture de fichiers
df = pd.read_csv(file, sep=";")
##### Etape 2 Evaluer les critères
criteria_idx = 1
# Critère 1 nightime symptoms
mask = (df['q3'] >= 3) | (df['q4'] >= 3) | (df['q5'] >= 3)
df[f"Critere {criteria_idx}"] = 0
df.loc[mask, f"Critere {criteria_idx}"] = 1
criteria_idx += 1

# Critère 2 Duration
mask = (df['q6'] >= 3)
df[f"Critere {criteria_idx}"] = 0
df.loc[mask, f"Critere {criteria_idx}"] = 1
criteria_idx += 1

# Critère 3 Daytime
mask = (df['q7'] >= 1)
df[f"Critere {criteria_idx}"] = 0
df.loc[mask, f"Critere {criteria_idx}"] = 1
criteria_idx += 1

# Critère 4 Not attributable to environment
mask = (df['q8'] <= 1)
df[f"Critere {criteria_idx}"] = 0
df.loc[mask, f"Critere {criteria_idx}"] = 1
criteria_idx += 1

# Critère 5 Non-substance
mask = (df['q10'] > 1)
df[f"Critere {criteria_idx}"] = 1
df.loc[mask, f"Critere {criteria_idx}"] = 0
criteria_idx += 1

# Critère 6 Non-disease
mask = (df['q12'] > 2)
df[f"Critere {criteria_idx}"] = 1
df.loc[mask, f"Critere {criteria_idx}"] = 0
criteria_idx += 1

# Critère 7 Special Cases
mask = (df['q13_rien'] == 0) & (df['isi_4'] >= 3)
df[f"Critere {criteria_idx}"] = 0
df.loc[mask, f"Critere {criteria_idx}"] = 1
criteria_idx += 1

# Q10 0, 1 ou rien c'est oui


##### Etape 3 Combiner les critères
df["Insomnie"] = "Pas d'Insomnie"
mask = ((df['Critere 1'] == 1) & (df['Critere 2'] == 1) & (df['Critere 3'] == 1) & (df['Critere 4'] == 1)\
       & (df['Critere 5'] == 1) & (df['Critere 6'] == 1)) | (df['Critere 7'] == 1)
df.loc[mask, "Insomnie"] = "Insomnie"

res = df[["id", "date", "age", "height", "weight", "genre", "studies", "csp",
          "Critere 1", "Critere 2", "Critere 3", "Critere 4", "Critere 5", "Critere 6", "Critere 7", "Insomnie"]].copy()

print(f"Sujets avec Insomnies ({len(df[df['Insomnie'] == 'Insomnie'])} / {len(df)})")
res.to_csv(f"{filename}_Result.csv", sep=";", index=False)
