# Contributing

Contributions are actively welcome!

## Local Setup

Create a virtualenv for local development using your tool of choice. If you're using pyenv and pyenv-virtualenv:

```sh
pyenv virtualenv 3.8.5 flask-resty
pyenv local flask-resty
```

Install dependencies:

```sh
# optionally include [jwt] for the full test suite, but requires cryptography,
#  and its dependent binary libraries
pip install -e .[dev]
```

### Running tests

Tests can be run for your current enviroment by running pytest directly:

```sh
pytest
```

To run formatting and syntax checks:

```sh
tox -e lint
```

To run tests in all supported Python versions in their own virtual environments (must have each interpreter installed):

```sh
tox
```

### Documentation

Contributions to the documentation are welcome. Documentation is written in reStructuredText (rST). A quick rST reference can be found [here](https://docutils.sourceforge.io/docs/user/rst/quickref.html). Builds are powered by Sphinx.

To build the docs in "watch" mode:

```sh
tox -e watch-docs
```

Changes in the `docs/` directory will automatically trigger a rebuild.
