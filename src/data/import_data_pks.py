import sys
from typing import Annotated
from textwrap import wrap

import pandas as pd

from src.data.config import colname_map, select_columns
from src.visualization.visualize import make_df_colormap


sys.path.append("..")  # necessary when used by a notebook


# loading function takes over column selection, naming, historization and string cleaning:
def _load_n_trim(dir, yr, columns):
    """
    Hilfsfunktion.
    Lädt einen DataFrame und 
    """
    data = (pd.read_excel(f"{dir}/PKS{yr}.xlsx")[columns]
            .set_axis(['key', 'label', 'state', 'count', 'freq', 'attempts', 'clearance'], axis=1)
            .rename(colname_map)
            .assign(**{"year": yr})
            )

    # remove non-breaking spaces
    data.label = data.label.str.replace(u"\xa0", u" ")

    return data


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
    data.set_index(["year", "state", "key",
                   "label"], inplace=True)
    data.sort_index(inplace=True)
    data.reset_index(inplace=True)

    if format == "parquet":
        data.to_parquet(outfilepath)

    elif format == "csv":
        data.to_csv(outfilepath)


# def clean_sum_keys(infilepath: str, outfilepath: str, format: str = "parquet") -> None:
#     """
#     Summenschlüssel ausschließen.
#     Dies sind vom Amt selber erstellte beliebige Kollektionen von Schlüsseln.
#     Darunter welche, die "*" enthalten.
#     """
#     df = pd.read_parquet(infilepath)
#     df = df.loc[df.Schlüssel.str.match("^[0-9]+$")]
#     df = df.loc[df.Schlüssel.astype(int).lt(890000)]

#     if format == "parquet":
#         df.to_parquet(outfilepath)

#     elif format == "csv":
#         df.to_csv(outfilepath)


def hierarchize_keys(keylist: pd.Series, parent_col_name="parent", level_col_name="level") -> pd.DataFrame:
    """
    Takes a unique key list, returns inferred levels and parents.

    Starting with a sorted list of unique keys, the rule gets applied with every step down the list:
    - L = leftmost character that changes; = level of the next key
    - 
    """
    level = level_col_name
    parent = parent_col_name
    
    
    # the shape of the result:
    df = pd.DataFrame({"key": keylist,
                       level: None,
                       parent: None})

    # (1) level: identify the level at which a key resides
    
    df[level].iloc[0] = 1

    for k in range(1, len(df)):
        key_i = df.key.iloc[k-1]
        key_j = df.key.iloc[k]

        # this key's leftmost character change = level:
        for digit in range(6):
            if key_j[digit] != key_i[digit]:
                this_level = digit + 1
                break

        df[level][k] = this_level

    # (2) parent: infer parent from whether each key is lower, higher or equal to its predecessor

    # level: |dummy|       1       |  2  |  3  |  4  |  5  |  6  |
    parents = [None, df.key.iloc[0], None, None, None, None, None]
    
    for k in range(1, len(df)):
        predecessor_level = df[level].iloc[k-1]
        this_keys_level = df[level].iloc[k]
        
        if this_keys_level == 1:
            df[parent].iloc[k] = None
            parents[1] = df.key.iloc[k]
            
        elif this_keys_level > predecessor_level:
            df[parent].iloc[k] = df.key.iloc[k-1]
            parents[this_keys_level] = df.key.iloc[k]
            
        elif this_keys_level < predecessor_level:
            # this works but should have a clearer structure.
            search_area = df.loc[df.key.lt(df.key.iloc[k])]  # look at all above
            search_area = search_area.loc[search_area[level].lt(df[level].iloc[k])]  # limit to higher levels
            last_higher_level = search_area[level].iloc[-1]  # level of the last higher key
            df[parent].iloc[k] = parents[last_higher_level]
            parents[this_keys_level] = df.key.iloc[k]
            
        elif this_keys_level == predecessor_level:
            # this works but should have a clearer structure.
            search_area = df.loc[df.key.lt(df.key.iloc[k])]  # look at all above
            search_area = search_area.loc[search_area[level].lt(df[level].iloc[k])]  # limit to higher levels
            last_higher_level = search_area[level].iloc[-1]  # level of the last higher key
            df[parent].iloc[k] = parents[last_higher_level]
            parents[this_keys_level] = df.key.iloc[k]

    return df


def hierarchize_data(data: pd.DataFrame, parent_col_name="parent", level_col_name="level") -> pd.DataFrame:

    data = data.loc[~data.key.eq("------")]

    allkeys = data.key.drop_duplicates()

    # extra treatment for keys containing asterisks, as they all concern one theme (theft),
    # and because they otherwise cause lots of headache in hierarchization:
    asterisk_keys = (allkeys
                     .loc[allkeys.str.contains("*", regex=False)]
                     .sort_values()
                     .reset_index(drop=True)
                     )
    numeric_keys = (allkeys
                    .loc[~allkeys.isin(asterisk_keys)]
                    .sort_values()
                    .reset_index(drop=True)
                    )

    # every key gets a parent based on the algorithm in hierarchize_keys():
    hierarchy = pd.concat([
        hierarchize_keys(
            asterisk_keys, parent_col_name=parent_col_name, level_col_name=level_col_name),
        hierarchize_keys(
            numeric_keys, parent_col_name=parent_col_name, level_col_name=level_col_name)
    ]).set_index("key")

    # join this hierarchy information to the actual crime data:
    data_hier = (data
                 .set_index("key")
                 .join(hierarchy, how="left")
                 .reset_index()
                 )

    return (data_hier)


def clean_labels(data: pd.DataFrame) -> pd.DataFrame:
    
    # nonbreaking spaces
    data.label = data.label.str.replace(r"[\u00A0]", " ", regex=True)
    
    # leading/trailing spaces
    data.label = data.label.str.strip()

    removables = [
        r"§.*$",
        r".und zwar.*$",
        r".darunter:.*$",
        r".gemäß.?$",
        r".gem\..?$",
        r".davon:.?$",
        r".nach.?$",
    ]
    for removable in removables:
        data.label = data.label.str.replace(removable, "", regex=True)
    
    
    
    # linebreak for especially long labels:
    data.label = data.apply(lambda x: "<br>".join(wrap(x.label, 100)), axis=1)
    
    return data


def mark_labelchange(data: pd.DataFrame) -> pd.DataFrame:
    """
    Mark where the label of a key has changed compared to the previous year.
    """
    data = data.sort_values(["state", "key", "year"])
    data["label_change"] = False

    data_temp = pd.DataFrame()

    for i, grp in data.groupby(["state", "key", "label"]):
        this = grp.copy().reset_index()
        this.loc[this.index[0], "label_change"] = True
        data_temp = pd.concat([data_temp, this])
    data = data_temp.sort_values(["key", "year"])
    
    return data


if __name__ == "__main__":

    # transport the data from Excel files to a processable form without much processing:
    import_data(indirpath="data/raw/",
                outfilepath="data/interim/pks.parquet")

    data = pd.read_parquet("data/interim/pks.parquet")

    # clean labels from §§ and so on, then mark label changes:
    data_clean = mark_labelchange(clean_labels(data))
    
    data_hr = hierarchize_data(data_clean)
    global_colormap = make_df_colormap(data_hr)
    data_hr["color"] = data_hr.key.apply(
        lambda key: global_colormap[key])

    data_hr = data_hr.drop(["level", "parent"], axis=1)

    data_hr.to_parquet("data/processed/pks.parquet")
