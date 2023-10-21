from typing import Annotated

import pandas as pd

from src.data.config import colname_map, select_columns
from src.data.parents import add_level_parent

RAWDIR = "data/raw/"
PROCESSEDFILE = "data/interim/pks.csv"


# angepasste Ladefunktion, übernimmt Spaltenauswahl und -Benennung sowie Historisierung
def _load_n_trim(dir, yr, columns):
    """
    Hilfsfunktion.
    Lädt einen DataFrame und 
    """
    return (pd.read_excel(f"{dir}/PKS{yr}.xlsx")[columns]
            .set_axis(['Schlüssel', 'Straftat', 'Bundesland', 'Fallzahl', 'je100k', 'versucht', 'aufgeklärt'], axis=1)
            .rename(colname_map)
            .assign(**{"Jahr": yr})
           )


def import_data(indirpath: Annotated[str, "Quellordner mit den Excel-Dateien"],
                outfilepath: Annotated[str, "Zielordner und -Dateiname für die CSV-Datei"]) -> None:
    """
    Daten aus den heruntergeladenen Excel-Dateien in einen sauberen Datenframe importieren.
    """
    data = pd.concat([_load_n_trim(indirpath, yr, columns) for yr, columns in select_columns.items()])

    # Label 'Bund' vereinheitlichen:
    data.replace({"Bund echte Zählung der Tatverdächtigen": "Bund",
                "Bundesrepublik Deutschland": "Bund"}, inplace=True)
    # Index und Sortierung:
    data.set_index(["Jahr", "Bundesland", "Schlüssel", "Straftat"], inplace=True)
    data.sort_index(inplace=True)

    data.to_csv(outfilepath)


if __name__ == "__main__":
    
    import_data(indirpath=RAWDIR, outfilepath=PROCESSEDFILE)
    data = pd.read_csv(PROCESSEDFILE)
    data = add_level_parent(data)