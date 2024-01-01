import colorsys

import pandas as pd
import numpy as np


def hsv_to_css(h, s, v):
    """
    Convert HSV tuple into css string
    """
    rgb = map(lambda x: int(x * 255), colorsys.hsv_to_rgb(h,s,v))
    return '#%02x%02x%02x' % tuple(rgb)


def hsvtraj(n, ha=0, hb=1, sa=1, sb=1, va=.5, vb=.5, he=1, se=1, ve=1, fmt="hsv"):
    """
    return a list of colorstrings in hsv, rgb or hex format defined by
    a trajectory through HSV space defined by the start (a) and end (b)
    points in each dimension and an exponent that describes curvature.
    Exponent 1 is a straight line, 2 is a parable, -2 sqroot.
    """
    # exponents may not be negative, value & saturation must be 0...1:
    assert (he > 0 and se > 0 and ve > 0
            and sa >= 0 and sa <= 1 and sb >= 0 and sb <= 1
            and va >= 0 and va <= 1 and vb >= 0 and vb <= 1
    )
    
    # special case n=1:
    if n == 1:
        return [((ha+hb)/2, (sa+sb)/2, (va+vb)/2)]
    
    # make curvature
    unit_distance = np.arange(0, (1+1/n), 1/(n-1))
    std_curve_h = unit_distance ** he
    std_curve_s = unit_distance ** se
    std_curve_v = unit_distance ** ve
    
    # scale the curve to a..b
    curve_h = [ha + (hb-ha)*i for i in std_curve_h]
    curve_s = [sa + (sb-sa)*i for i in std_curve_s]
    curve_v = [va + (vb-va)*i for i in std_curve_v]
    
    # make hue cyclical:
    curve_h = [i % 1 for i in curve_h]
    
    if fmt == "hsv":
        return list(zip(curve_h, curve_s, curve_v))
    elif fmt == "rgb":
        return [colorsys.hsv_to_rgb(h,s,v) for h,s,v in zip(curve_h, curve_s, curve_v)]
    elif fmt == "css":
        hex_out = []
        for h,s,v in zip(curve_h, curve_s, curve_v):
            hex_out.append(hsv_to_css(h,s,v))
        return hex_out


def max_nchildren(df, parent_col="parent"):
    """
    For a df with hierarchical categories that denote their parent using the "parent" column,
    return the maximum number of children a category has.
    
    :param df: the dataframe
    :param parent_col: name of the column that denotes the parent
    """
    max_nchildren = 0
    for key, grp in df.groupby(parent_col):
        if len(grp) > max_nchildren:
            max_nchildren = len(grp)
    
    return max_nchildren


