from typing import Annotated

import pandas as pd

from src.data.config import colname_map, select_columns
from src.data.parents import add_parent


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
                outfilepath: Annotated[str, "Zielordner und -Dateiname für die CSV-Datei"],
                format: str = "parquet") -> None:
    """
    Daten aus den heruntergeladenen Excel-Dateien in einen sauberen Datenframe importieren.
    """
    data = pd.concat([_load_n_trim(indirpath, yr, columns)
                     for yr, columns in select_columns.items()])

    # Label 'Bund' vereinheitlichen:
    data.replace({"Bund echte Zählung der Tatverdächtigen": "Bund",
                  "Bundesrepublik Deutschland": "Bund"}, inplace=True)
    # Index und Sortierung:
    data.set_index(["Jahr", "Bundesland", "Schlüssel",
                   "Straftat"], inplace=True)
    data.sort_index(inplace=True)
    data.reset_index(inplace=True)

    if format == "parquet":
        data.to_parquet(outfilepath)

    elif format == "csv":
        data.to_csv(outfilepath)


def clean_sum_keys(infilepath: str, outfilepath: str, format: str = "parquet") -> None:
    """
    Summenschlüssel ausschließen.
    Dies sind vom Amt selber erstellte beliebige Kollektionen von Schlüsseln.
    Darunter welche, die "*" enthalten.
    """
    df = pd.read_parquet(infilepath)
    df = df.loc[df.Schlüssel.str.match("^[0-9]+$")]
    df = df.loc[df.Schlüssel.astype(int).lt(890000)]

    if format == "parquet":
        df.to_parquet(outfilepath)

    elif format == "csv":
        df.to_csv(outfilepath)


if __name__ == "__main__":

    import_data(indirpath="data/raw/",
                outfilepath="data/interim/pks.parquet")
    clean_sum_keys(infilepath="data/interim/pks.parquet",
                   outfilepath="data/processed/pks.parquet")
