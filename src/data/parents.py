"""
Wir erstellen uns einen Straftatenkatalog mit Abbildung der Hierarchie zwischen Delikten.
Zweck ist der Sunburst-Chart zur Auswahl von Delikten und die geordnete Darstellung
der Daten.
"""
from typing import Tuple
import pandas as pd
import numpy as np


def _recur_key(key: str, array: pd.Series, RDEPTH):
    """
    Der innere, rekursive Teil der "parent"-Fkt.; gibt denjenigen Schlüssel
    zurück, von dem die meisten Stellen von links beginnend in den jeweiligen
    Zielschlüssel passen. Das ist der Oberschlüssel.
    """
    RDEPTH += 1
    if RDEPTH > 10:
        print(f"offending key: {key}; depth: {RDEPTH}")
    found = array.loc[array.str.match(rf"^{key[0:-1]}$")]
    if len(found) == 0:
        found = _recur_key(key[0:-1], array, RDEPTH)
    return found


def _parent(key: str, array: pd.Series):
    """
    Gibt den Oberschlüssel eines gegebenen (Ziel-)Schlüssels wieder. Regelt
    die Typkonvertierung von Series zu str.
    """
    if len(key) < 2:
        return None
    else:
        recur_depth = 0
        res = _recur_key(key, array, recur_depth).iloc[0]

    return res


def add_level_parent(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ermittelt aus einer PKS-Tabelle hierarchische Zusammenhänge zwischen Schlüsseln
    und fügt die Spalten "level" und "parent" hinzu.
    """

    # Summenschlüssel ausschließen.
    # Dies sind vom Amt selber erstellte beliebige Kollektionen von Schlüsseln.
    # Darunter welche, die "*" enthalten:
    df = df.loc[df.Schlüssel.str.match("^[0-9]+$")]

    # sowie weitere, die sich auch außerhalb der eigentlichen Hierarchie bewegen:
    df = df.loc[df.Schlüssel.astype(int).lt(890000)]

    # Nullen am Ende löschen; hilft bei der weiteren Verarbeitung, wird später
    # wieder aufgefüllt:
    keys = (df.Schlüssel
            .replace(r"0+$", "", regex=True)
            .replace("", "0")
            )

    # duplikatfreies Register erstellen für die hierarchischen Beziehungen zwischen
    # den Schlüsseln;
    #
    # unique Liste aller Schlüssel:
    klp = (pd.DataFrame({"key": keys})
           .drop_duplicates(subset="key")
           .reset_index(drop=True)
           )
    # "level": leer, bis auf die höchsten Schlüssel ("_00000"), die Ebene 1 sind:
    klp["level"] = klp.key.apply(lambda x: 1 if len(x) == 1 else 0)

    # Suche des Oberschlüssels für jeden Schlüssel anwenden:
    klp["parent"] = klp.key.apply(lambda x: _parent(x, klp.key))

    # Nullen wieder auffüllen:
    klp.key = klp.key.str.pad(6, side="right", fillchar="0")
    klp.parent = klp.parent.str.pad(6, side="right", fillchar="0")

    # Ebene: Oberschlüssel aufsuchen (ist immer oberhalb in der Tabelle), Ebene
    # dort ablesen und +1 speichern:
    for i, row in klp.iterrows():
        parents_level = klp.loc[klp.key == row["parent"], "level"]
        klp.at[i, "level"] = 1 if len(
            parents_level) == 0 else parents_level.iloc[0] + 1

    # PKS-Daten um die Hierarchiedaten erweitern:
    df = pd.merge(df, klp,
                  how="left",
                  left_on="Schlüssel",
                  right_on="key")

    return df
