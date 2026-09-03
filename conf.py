# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pathlib import Path

# -- Project information -----------------------------------------------------

project = 'APX'
copyright = '2026, Conny Gustafsson'
author = 'Conny Gustafsson'
release = 'v1.3'

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
    'implementations/**',
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

plantuml = f'java -jar {Path.home() / "plantuml" / "plantuml.jar"}'
plantuml_output_format = 'svg_img'
