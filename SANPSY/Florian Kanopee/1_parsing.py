""" Parsing du Json Kanopee """

import json

import pandas as pd

filename = "all_kanopee"

# Si on est obligé de couper en plusieurs fichiers (avec une selection des clés avant le passage en dataframe le découpage n'est plus necessaire)
n_per_files = 100000

# Limite concernant le nombre d'éléments dans une liste par exemple le nombre de nuits)
limit_list = 20

##################################################
def flatten_json(data: str, prefix: str = '') -> dict:
    """
    "Applati" l'élément (les éléments étant des listes deviennent des clés)
    :param data: Element json à "applatir"
    :param prefix: Parent de l'élément
    :return: Elément "applati"
    """
    if isinstance(data, dict):
        flattened = {}
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            flattened.update(flatten_json(value, new_key))
        return flattened
    elif isinstance(data, list):
        flattened = {}
        for i, item in enumerate(data):
            if i > limit_list: continue
            flattened.update(flatten_json(item, f"{prefix}.{i}"))
        return flattened
    else:
        return {prefix: data}

##################################################
def filter_dict_by_key(dictionnaire: dict, chaine: str) -> dict:
    """
    Supprime les éléments dont la clé contient la chaine en paramètre.
    :param dictionnaire: Dictionnaire de base
    :param chaine: Chaine désignant les clés à supprimer
    :return: Un nouveau dictionnaire filtré.
    """
    return {key: value for key, value in dictionnaire.items() if chaine not in key}

##################################################
print(f"Ouverture du fichier : {filename}.json")
with open(f"{filename}.json") as json_file:
    json_data = json.load(json_file)

print("\"Applatissement\" du fichier")
flatten_data = [flatten_json(item) for item in json_data]

print("Suppression de certaines categories (ex : Metrics)")
flatten_data = [filter_dict_by_key(item, "Metrics") for item in flatten_data]

print("Conversion en dataframes")
for i in range(0, len(flatten_data) + 1, n_per_files):
    end = min(i + n_per_files, len(flatten_data))
    print(f"    Partie de {i} a {end}", end=", ")
    df = pd.DataFrame(flatten_data[i:end])
    print(f"{len(df.columns)} colonnes.")
    df.to_csv(f"{filename}_{i}.csv", index=False)

print("Fini.")
