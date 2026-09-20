# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import shutil

# -- Project information -----------------------------------------------------

project = 'APX'
copyright = '2026, Conny Gustafsson'
author = 'Conny Gustafsson'
release = '0.2'

# -- General configuration ---------------------------------------------------

extensions = [
    'myst_parser',
    'sphinx_design',
    'sphinx.ext.githubpages',
    'sphinxcontrib.mermaid',
    'sphinxcontrib.plantuml',
]

templates_path = ['_templates']
exclude_patterns = [
    '_build',
    '.venv',
    'README.md',
    'AGENTS.md',
    'TODO.md',
]

# MyST Parser configuration
myst_enable_extensions = [
    'colon_fence',
    'dollarmath',
    'amsmath',
    'attrs_inline',
    'attrs_block',
    'deflist',
    'fieldlist',
]

myst_heading_anchors = 4

# -- Options for HTML output -------------------------------------------------

html_theme = 'furo'
html_title = 'APX Documentation'
html_static_path = ['_static']
html_css_files = [
    'custom.css',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

if plantuml_jar := os.environ.get('PLANTUML_JAR'):
    plantuml = f'java -jar {plantuml_jar}'
elif os.path.exists('/tmp/plantuml.jar'):
    plantuml = 'java -jar /tmp/plantuml.jar'
elif (user_plantuml := os.path.expanduser('~/plantuml/plantuml.jar')) and os.path.exists(user_plantuml):
    plantuml = f'java -jar {user_plantuml}'
elif os.path.exists('/usr/share/plantuml/plantuml.jar'):
    plantuml = 'java -jar /usr/share/plantuml/plantuml.jar'
elif shutil.which('plantuml'):
    plantuml = shutil.which('plantuml')
else:
    raise RuntimeError(
        "PLANTUML_JAR environment variable not set, and plantuml was not found in standard paths (/tmp/plantuml.jar, ~/plantuml/plantuml.jar)."
    )

plantuml_output_format = 'svg_img'
