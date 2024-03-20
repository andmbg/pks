# Daten laden: aus variabel benannten Excel-Tabellen einen ordentlichen Datensatz machen.
# Die Selektion der Spalten ist Handarbeit. Bei jedem neuen Jahrgang müssen wir schauen,
# ob sich die Form geändert hat, und entsprechend anpassen.
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
    2022: ['Schlüssel',    'Straftat', 'Bundesland', 'Anzahl erfasste Fälle', 'HZ',             'erfasste Fälle davon: Versuche', 'Aufklärung']
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
