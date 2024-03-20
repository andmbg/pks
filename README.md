# Polizeiliche Kriminalstatistik
*Browseable crime statistics from the German Federal Police (Bundeskriminalamt, BKA)*

This is a dashboard that makes the annually published crime stats more accessible. The Federal Police publish a table per year that subsumes crimes under 6-digit keys and for each key states the rate of incidents, including punishable attempts. More attributes are published, namely perpetrators' gender and whether they were German nationals; but we focus only on incidents and attempts.

The dashboard lets you hierarchically browse those 6-digit keys and view their development as time series, also comparing Federal States. Under the hood, this repo also contains code that imports the (less than clean) raw data and infers the hierarchical key structure.

## Installation

To run this app locally as a standalone browser app, follow these steps upon cloning and `cd`'ing into this directory:

``` bash
make install
```

The app is ready to go now. Run it with

``` bash
make run
```

Open a browser and visit `localhost:8080` or `127.0.0.1:8080`.

## Data replication

The imported dataset has originally been included with this repository. If it is missing, it can be reproduced from the raw data files in `data/raw/`, which are Excel files directly taken from the relevant website (BKA) and unchanged. Yes, reproducible data are important.

The import job will take < 5 minutes:

``` bash
make data
```
