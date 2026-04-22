import pandas as pd

dtype = {
    "Libellé civilité d'exercice": "str",
    "Libellé type savoir-faire": "str",
    "Code postal (coord. structure)": "str",
}

df = pd.read_csv(
    "./data/praticiens.txt",
    sep="|",
    header=0,
    dtype=dtype,
    usecols=[
        "Libellé civilité d'exercice",
        "Libellé civilité",
        "Nom d'exercice",
        "Prénom d'exercice",
        "Libellé profession",
        "Libellé type savoir-faire",
        "Code mode exercice",
        "Numéro Voie (coord. structure)",
        "Libellé type de voie (coord. structure)",
        "Libellé Voie (coord. structure)",
        "Code postal (coord. structure)",
        "Libellé commune (coord. structure)",
        "Libellé secteur d'activité",
    ],
)
print(df.head())
# df.to_csv("./data/praticiens.csv")
