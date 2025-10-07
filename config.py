# Darstellung: Wie viele Schlüssel werden max. in der Zeitreihe angezeigt?
MAXKEYS = 4

# The dashboard is bilingual (might add yet more but let's not get carried away).
# So here is where we set which two languages we want to support. Their values are
# the technical codes that DeepL expects for translation queries. "de" can be con-
# sidered the default, as the data are German.
language_codes = {
    "de": "DE",
    "en": "EN-GB",
}

# Daten laden: aus variabel benannten Excel-Tabellen einen ordentlichen Datensatz machen.
# Die Selektion der Spalten ist Handarbeit (so wie anscheinend auch die Erstellung der PKS).
# Bei jedem neuen Jahrgang müssen wir schauen, ob sich die Form geändert hat, und
# entsprechend anpassen.
select_columns = {
    2013: ['Strft. Schl.', 'Straftat', 'Bundesland', 'erfasste Fälle 2013',   'HZ nach Zensus', 'Versuche absolut',               'aufgeklärte Fälle'],
    2014: ['Strft. Schl.', 'Straftat', 'Bundesland', 'erfasste Fälle 2014' ,  'HZ nach Zensus', 'Versuche absolut',               'aufgeklärte Fälle'],
    2015: ['Schlüssel',    'Straftat', 'Bundesland', 'erfasste Fälle',        'HZ nach Zensus', 'von Spalte 4 Versuche',          'Aufklärung'],
    2016: ['Schlüssel',    'Straftat', 'Bundesland', 'erfasste Fälle',        'HZ nach Zensus', 'von Spalte 4 Versuche',          'Aufklärung'],
    2017: ['Schlüssel',    'Straftat', 'Bundesland', 'erfasste Fälle',        'HZ nach Zensus', 'von Spalte 4 Versuche',          'Aufklärung'],
    2018: ['Schlüssel',    'Straftat', 'Bundesland', 'erfasste Fälle',        'HZ nach Zensus', 'von Spalte 4 Versuche',          'Aufklärung'],
    2019: ['Schlüssel',    'Straftat', 'Bundesland', 'erfasste Fälle',        'HZ nach Zensus', 'von Spalte 4 Versuche',          'Aufklärung'],
    2020: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung'],
    2021: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung'],
    2022: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung'],
    2023: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung'],
    2024: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung'],
}

# Spaltenbenennung vereinheitlichen
# Muss bei Formänderungen oben auch ggf. angepasst werden.
colname_map = {
    "Strft. Schl.": "Schlüssel",
    ('erfasste Fälle 2013', 'erfasste Fälle 2014', "erfasste Fälle", "Anzahl erfasste Fälle"): "Fallzahl",
    ("HZ nach Zensus", "HZ"): "je100k",
    ("Versuche absolut", "von Spalte 4 Versuche", "erfasste Fälle davon: Versuche"): "versucht",
    ("aufgeklärte Fälle", "Aufklärung"): "aufgeklärt"
}
