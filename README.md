# APX Documentation

This is the documentation repository for APX (AUTOSAR Port eXchange), built using Sphinx.

This project is a work in progress.

## Installation steps

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt 
```

### Windows

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt 
```

## Building the Documentation


Build the HTML documentation once:

```bash
python -m sphinx -b html . _build/html
```

To rebuild automatically when documentation files change and preview the site
with live reload, run:

```bash
sphinx-autobuild . _build/html
```

The preview server is available at <http://127.0.0.1:8000> by default. Stop it
with `Ctrl+C`.
