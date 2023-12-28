import sys
import os
from typing import Annotated
from textwrap import wrap, shorten
import logging

import pandas as pd

from ..data.config import colname_map, select_columns
from ..visualization.visualize import make_df_colormap


sys.path.append("..")  # necessary when used by a notebook
logging.basicConfig(
    filename="data_import.log",
    level=logging.DEBUG,      # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s %(levelname)s %(message)s",
    filemode="w"
)


# loading function takes over column selection, naming, historization and string cleaning:
def _load_n_trim(dir, yr, columns):
    """
    Hilfsfunktion.
    Lädt einen DataFrame und 
    """
    logging.info(f"Opening Excel file PKS{yr}.xlsx.")
    data = (pd.read_excel(f"{dir}/PKS{yr}.xlsx")[columns]
            .set_axis(['key', 'label', 'state', 'count', 'freq', 'attempts', 'clearance'], axis=1)
            .rename(colname_map)
            .assign(**{"year": yr})
            )

    # remove non-breaking spaces
    data.label = data.label.str.replace(u"\xa0", u" ")

    return data


def import_data(indirpath: Annotated[str, "Quellordner mit den Excel-Dateien"],
                outfilepath: Annotated[str, "Zielordner und -Dateiname für die parquet-Datei"],
                format: str = "parquet") -> None:
    """
    Daten aus den heruntergeladenen Excel-Dateien in einen sauberen Datenframe importieren.
    """
    logging.info(f"Importing Data from {indirpath} to {outfilepath}.")
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


def hierarchize_keys(keylist: pd.Series, parent_col_name="parent", level_col_name="level") -> pd.DataFrame:
    """
    Takes a unique key list, adds columns for inferred levels and parents.
    """
    logging.info(f"Hierarchizing key list of {len(keylist)} entries.")
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
            # this condition also allows having a digit change >1 places behind the parent, so
            # we can have children with level 4 to parents with level 2.
            df[parent].iloc[k] = df.key.iloc[k-1]
            parents[this_keys_level] = df.key.iloc[k]

        elif this_keys_level < predecessor_level:
            # this works but should have a clearer structure.
            # look at all above
            search_area = df.loc[df.key.lt(df.key.iloc[k])]
            search_area = search_area.loc[search_area[level].lt(
                df[level].iloc[k])]  # limit to higher levels
            # level of the last higher key
            last_higher_level = search_area[level].iloc[-1]
            df[parent].iloc[k] = parents[last_higher_level]
            parents[this_keys_level] = df.key.iloc[k]

        elif this_keys_level == predecessor_level:
            # this works but should have a clearer structure.
            # look at all above
            search_area = df.loc[df.key.lt(df.key.iloc[k])]
            search_area = search_area.loc[search_area[level].lt(
                df[level].iloc[k])]  # limit to higher levels
            # level of the last higher key
            last_higher_level = search_area[level].iloc[-1]
            df[parent].iloc[k] = parents[last_higher_level]
            parents[this_keys_level] = df.key.iloc[k]
    
    # it's got hierarchy now, but we have children of level > n+1 to parents of level n.
    # re-set levels to "your parent's level + 1":
    for lab, grp in df.groupby(["level", "parent"], sort=True):
        parents_level = df.loc[df.key.eq(lab[1]), "level"].iloc[0]
        df.loc[df.parent.eq(lab[1]), "level"] = parents_level + 1

    return df


def hierarchize_data(data: pd.DataFrame, parent_col_name: str = "parent", level_col_name: str = "level") -> pd.DataFrame:
    """
    Takes a PKS dataset and adds a column for level and parent denoting each entry's level and the name of its
    parent key.  Uses entirely the key numbers as a heuristic and treats keys with asterisks separately - they
    form a separate hierarchy that is joined with the rest.

    :param data: the PKS dataset
    :parent_col_name: if the name "parent" is not okay, set another one here
    :level_col_name: if the name "level" is not okay, set another one here
    """
    logging.info("Hierarchizing data.")
    
    data = data.filter(["year", "state", "key", "label", "shortlabel", "label_change", "count", "freq", "attempts", "clearance", "color"])

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
    keys_hierarchized = pd.concat([
        hierarchize_keys(
            asterisk_keys, parent_col_name=parent_col_name, level_col_name=level_col_name),
        hierarchize_keys(
            numeric_keys, parent_col_name=parent_col_name, level_col_name=level_col_name)
    ]).set_index("key")

    # make an artificial root; nicer initial sunburst display and easier computation of
    # section widths as next step:
    keys_hierarchized = pd.concat([
        pd.DataFrame({"key": ["Straftaten"],
                      "level": [0],
                      "parent": [None]}).set_index("key"),
        keys_hierarchized
    ])
    # change "None" parent to this new root for all level-1 entries:
    keys_hierarchized.loc[keys_hierarchized.level.eq(1), "parent"] = "Straftaten"
    
    # In order for plotly to space keys evenly on their level (instead of according to how
    # many total descendants they have), we need to work around the default by using its
    # display params. So here, we add an 'sb_angle' (sunburst angle) column that encodes
    # this width:
    df = keys_hierarchized.copy().reset_index()
 
    df["sectionwidth"] = 0.0
    df["width_on_level"] = None
    df.loc[df.level.eq(0), "sectionwidth"] = 1.0
    df.loc[df.level.eq(0), "width_on_level"] = 1
    df.loc[df.level.eq(0), "parent"] = None

    logging.debug("Setting the section widths for keys.")

    for level in range(7):
        
        for parent, siblings_df in df.loc[df.level.eq(level)].groupby("parent"):
            width_on_level = 1 / len(siblings_df)
            parent_width = df.loc[df.key.eq(parent), "sectionwidth"].iloc[0]
            sectionwidth = parent_width * width_on_level

            df.loc[df.parent.eq(parent), "width_on_level"] = width_on_level
            df.loc[df.parent.eq(parent), "sectionwidth"] = sectionwidth

    df = df.drop("width_on_level", axis=1)

    # join this hierarchy information to the actual crime data:
    data_hier = pd.merge(
        data,
        df,
        on="key",
        how="left"
    ).reset_index()
    # data_hier = (data
    #              .set_index("key")
    #              .join(df, how="left")
    #              .reset_index()
    #              )

    return (data_hier)


def clean_labels(data: pd.DataFrame) -> pd.DataFrame:
    
    logging.info("Cleaning labels.")

    # nonbreaking spaces
    data.label = data.label.str.replace(r"[\u00A0]", " ", regex=True)

    # leading/trailing spaces
    data.label = data.label.str.strip()

    # create an abbreviated label column for annotations
    # (full labels can still go into the tooltips):
    data["shortlabel"] = data.label
    removables = [
        r"§.*$",
        r".und zwar.*$",
        r".darunter:.*$",
        r".gemäß.?$",
        r".gem\..?$",
        r".davon:.?$",
        r".nach.?$",
    ]

    replacements = {
        r"insgesamt": "insg.",
        r"dergleichen": "dgl.",
    }

    for removable in removables:
        data.shortlabel = data.shortlabel.str.replace(
            removable, "", regex=True)

    for pat, repl in replacements.items():
        data.shortlabel = data.shortlabel.str.replace(pat, repl, regex=True)

    data.shortlabel = data.apply(lambda row: shorten(
        row.shortlabel, width=90, placeholder="..."), axis=1)

    # for the full-length labels, add linebreaks for especially long exemplars:
    data.label = data.apply(lambda x: "<br>".join(wrap(x.label, 100)), axis=1)

    return data


def mark_labelchange(data: pd.DataFrame) -> pd.DataFrame:
    """
    Mark where the label of a key has changed compared to the previous year.
    """
    logging.info("Marking label changes for display.")
    data = data.sort_values(["state", "key", "year"])
    data["label_change"] = False

    data_temp = pd.DataFrame()

    for i, grp in data.groupby(["state", "key", "shortlabel"]):
        this = grp.copy().reset_index()
        this.loc[this.index[0], "label_change"] = True
        data_temp = pd.concat([data_temp, this])
    data = data_temp.sort_values(["key", "year"])

    return data


if __name__ == "__main__":

    # transport the data from Excel files to a processable form without much processing:
    
    logging.info("Checking if interim file already exists.")
    
    outfilepath = "data/interim/pks.parquet"

    if os.path.exists(outfilepath):
       logging.info("It does.")
    else:
        import_data(
            indirpath="data/raw/",
            outfilepath=outfilepath
        )

    data = pd.read_parquet("data/interim/pks.parquet")

    # clean labels from §§ and so on, then mark label changes:
    data_clean = clean_labels(data)
    data_marked = mark_labelchange(data_clean)

    data_hr = hierarchize_data(data_marked)
    global_colormap = make_df_colormap(data_hr)
    data_hr["color"] = data_hr.key.apply(
        lambda key: global_colormap[key])

    data_hr = data_hr.drop(["level", "parent"], axis=1)

    # manuelle Löschung störender Summenschlüssel
    data_hr = data_hr.loc[~data_hr.key.isin([
        # => englischsprachig
        "900230", "900250", "900251", "900252", "900253", "900260", "900261",
        # => bandenmäßiger Wohnungseinbruchdiebstahl mit Tageswohnungseinbruch (very special)
        "943520",
        "972500",  # => illegale Einreise + Aufenthalt (in 725... enthalten)
        # "973000",  # => Rauschgiftdelikte (in 730... enthalten)
        "980100",  # => "Cybercrime insg."
    ])]

    data_hr.drop("index", axis=1, inplace=True)

    logging.info("Saving imported and processed data to parquet.")
    data_hr.to_parquet("data/processed/pks.parquet")
