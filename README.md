# Installation

To run this app as a standalone browser app from localhost, follow these steps upon cloning and cd'ing into this directory:

``` bash
make install
```

Activate the virtual environment:

``` bash
source venv/bin/activate
```

Import the data (this will take a few minutes):

``` bash
make data
```

Run the app. Watch the command-line output for the URL (likely 'localhost:8050' or '127.0.0.1:8050').

``` bash
make run
```
