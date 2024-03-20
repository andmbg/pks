# Installation

To run this app as a standalone browser app from localhost, follow these steps upon cloning and `cd`'ing into this directory:

``` bash
make install
```

The imported dataset has originally been included with this repository. If it is missing, it can be reproduced from the raw data files in `data/raw/`, which are Excel files directly taken from the relevant website (BKA). Yes, reproducible data are important.

The import job will take < 5 minutes:

``` bash
make data
```

The app is ready to go now.

``` bash
make run
```

Open a browser and visit `localhost:8080` or `127.0.0.1:8080`.

