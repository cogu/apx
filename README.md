# APX Documentation

This is the documentation repository for APX (AUTOSAR Port eXchange), built using Sphinx.

This project is a work in progress.

## Prerequisites

Building the documentation (including PlantUML diagrams) requires:

1. **Python 3.10+**
2. **Java Runtime Environment (JRE)** (Java 17 or 21 recommended)
3. **Graphviz** (used by PlantUML for diagram rendering)
4. **PlantUML JAR** and the `PLANTUML_JAR` environment variable

### Installing System Dependencies

#### Linux (Ubuntu/Debian)

```bash
# Install Java and Graphviz
sudo apt update
sudo apt install -y openjdk-21-jre-headless graphviz

# Download PlantUML jar (e.g. to ~/plantuml/plantuml.jar)
mkdir -p ~/plantuml
curl -L -o ~/plantuml/plantuml.jar https://github.com/plantuml/plantuml/releases/latest/download/plantuml.jar

# Set the environment variable in your shell profile
echo 'export PLANTUML_JAR="$HOME/plantuml/plantuml.jar"' >> ~/.bashrc
source ~/.bashrc
```

#### Windows

1. Install Java (e.g. from [Adoptium Temurin](https://adoptium.net/)).
2. Install Graphviz (e.g. via `winget install Graphviz.Graphviz` or installer) and ensure `dot.exe` is in your `PATH`.
3. Download `plantuml.jar` from [PlantUML Releases](https://github.com/plantuml/plantuml/releases/latest).
4. Set the `PLANTUML_JAR` user environment variable to the absolute path of `plantuml.jar`.

## Python Environment Setup

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
```

> **Note:** For CI/deployment environments that only build the static site, `requirements.txt` contains the minimal production build dependencies without development tooling like `sphinx-autobuild`.

## Building the Documentation

### Single Build

Build the HTML documentation once:

```bash
python -m sphinx -b html . _build/html
```

### Live Reload Preview (Development)

To rebuild automatically when documentation files change and preview the site with live reload, run:

```bash
sphinx-autobuild . _build/html
```

The preview server is available at <http://127.0.0.1:8000> by default. Stop it with `Ctrl+C`.
