"""Entry point for the ``shell`` Flask-RESTy CLI commmand."""
# Code adapted from flask-konch
import click
import flask
import konch
from flask.cli import with_appcontext
from pathlib import Path

LOGO = r"""
  _____ _           _         ____  _____ ____ _____
 |  ___| | __ _ ___| | __    |  _ \| ____/ ___|_   _|   _
 | |_  | |/ _` / __| |/ /____| |_) |  _| \___ \ | || | | |
 |  _| | | (_| \__ \   <_____|  _ <| |___ ___) || || |_| |
 |_|   |_|\__,_|___/_|\_\    |_| \_\_____|____/ |_| \__, |
                                                    |___/
""".strip(
    "\n"
)

DEFAULTS = dict(
    RESTY_SHELL_CONTEXT={},
    RESTY_SHELL_LOGO=LOGO,
    RESTY_SHELL_PROMPT=None,
    RESTY_SHELL_OUTPUT=None,
    RESTY_SHELL_CONTEXT_FORMAT=None,
    RESTY_SHELL_IPY_AUTORELOAD=False,
    RESTY_SHELL_IPY_EXTENSIONS=None,
    RESTY_SHELL_IPY_COLORS="linux",
    RESTY_SHELL_IPY_HIGHLIGHTING_STYLE=None,
    RESTY_SHELL_PTPY_VI_MODE=False,
)


def get_models_context(app: flask.Flask) -> dict:
    try:
        db = app.extensions["sqlalchemy"].db
    except KeyError:  # pragma: no cover
        return {}

    ret = {
        "db": db,
        "session": db.session,
        "commit": db.session.commit,
        "rollback": db.session.rollback,
        "flush": db.session.flush,
    }
    models = {
        name: cls
        for name, cls in db.Model._decl_class_registry.items()
        if isinstance(cls, type) and issubclass(cls, db.Model)
    }
    ret.update(models)
    return ret


def get_schema_context() -> dict:
    try:
        from marshmallow import class_registry
    except ImportError:  # pragma: no cover
        return {}
    return {
        schema_name: classes[0]
        for schema_name, classes in class_registry._registry.items()
        if "." not in schema_name
    }


def get_banner(app: flask.Flask, logo=LOGO) -> str:
    info = f"Flask app: {click.style(app.name, fg='green')}"
    if "SQLALCHEMY_DATABASE_URI" in app.config:
        database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
        info += f", Database: {click.style(database_uri, fg='green')}"
    return f"{logo}\n{info}"


def format_section(title: str, section: dict) -> str:
    formatted_section = ", ".join(sorted(section.keys(), key=str.lower))
    formatted_title = click.style(f"{title}:", bold=True)
    return f"\n{formatted_title}\n{formatted_section}"


@click.command(
    help="Run an interactive shell with models and schemas automatically imported."
)
@click.option(
    "--shell", "-s", type=click.Choice(konch.SHELL_MAP.keys()), default="auto"
)
@click.option("--sqlalchemy-echo", is_flag=True)
@with_appcontext
def cli(shell: str, sqlalchemy_echo: bool):
    """An improved Flask shell command."""
    from flask.globals import _app_ctx_stack

    app = _app_ctx_stack.top.app
    options = {key: app.config.get(key, DEFAULTS[key]) for key in DEFAULTS}
    app.config["SQLALCHEMY_ECHO"] = sqlalchemy_echo
    base_context = {"app": app}
    flask_context = app.make_shell_context()
    schema_context = get_schema_context()
    context = dict(base_context)
    model_context = get_models_context(app)
    settings_context = options["RESTY_SHELL_CONTEXT"]

    def context_formatter(full_context: dict):
        """Flask-RESTy-specific context formatter. Groups objects
        into sections with a bold header for each.
        """
        sections = [("Flask", flask_context)]
        if schema_context:
            sections.append(("Schemas", schema_context))
        if model_context:
            sections.append(("Models", model_context))

        additional_context_keys = (
            full_context.keys()
            - flask_context.keys()
            - schema_context.keys()
            - model_context.keys()
        )
        additional_context = {
            key: full_context[key] for key in additional_context_keys
        }
        if additional_context:
            sections.append(("Additional", additional_context))
        return "\n".join([format_section(*section) for section in sections])

    context = {
        **flask_context,
        **schema_context,
        **model_context,
        **settings_context,
    }
    context_format = options["RESTY_SHELL_CONTEXT_FORMAT"] or context_formatter
    banner = get_banner(app, logo=options["RESTY_SHELL_LOGO"])
    # Use singleton _cfg to allow overrides in .konchrc.local
    config = konch._cfg
    config.update(
        dict(
            context=context,
            context_format=context_format,
            banner=banner,
            shell=shell,
            prompt=options["RESTY_SHELL_PROMPT"],
            output=options["RESTY_SHELL_OUTPUT"],
            ptpy_vi_mode=options["RESTY_SHELL_PTPY_VI_MODE"],
            ipy_extensions=options["RESTY_SHELL_IPY_EXTENSIONS"],
            ipy_autoreload=options["RESTY_SHELL_IPY_AUTORELOAD"],
            ipy_colors=options["RESTY_SHELL_IPY_COLORS"],
            ipy_highlighting_style=options[
                "RESTY_SHELL_IPY_HIGHLIGHTING_STYLE"
            ],
        )
    )
    if Path(".konchrc.local").exists():  # pragma: no cover
        konch.use_file(".konchrc.local", trust=True)

    konch.start(**config)
