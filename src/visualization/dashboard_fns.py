import json
import re

import pandas as pd

def sunburst_location(input_json: str):
    """
    Take the clickdata output of a sunburst plot and identify which item
    is currently active.
    
    :param input_json: str, the json string representing clickData sent
        by the sunburst plot
    :return: str, label of the active item in the plot
    """
    if input_json is None or input_json == "null":
        return "root"
    
    # clickData = json.loads(input_json)
    clickData = input_json
        
    # identifying location:
    # variables from the clickData:
    clickData = clickData["points"][0]
    entry = clickData["entry"]
    label = clickData["label"]
    path_match = re.search(r"([0-9]{6})/$", clickData["currentPath"])

    path_leaf = path_match[1] if path_match is not None else "root"
    
    # use those vars for the decision logic:
    if entry == "":
        location = label
    
    else:
        if int(entry) < int(label):
            location = label
        
        if entry == label:
            if path_leaf is None:
                location = "root"
            
            else:
                location = path_leaf
    
    return location
