import pytest
from click.testing import CliRunner
from flask.cli import ScriptInfo
from marshmallow import Schema, fields
from sqlalchemy import Column, Integer, String

from flask_resty.shell import cli


@pytest.fixture
def models(app, db):
    class Widget(db.Model):
        __tablename__ = "widgets"

        id = Column(Integer, primary_key=True)
        name = Column(String, nullable=False)
        description = Column(String)

    with app.app_context():
        db.create_all()

    yield {"widget": Widget}

    with app.app_context():
        db.drop_all()


@pytest.fixture
def schemas():
    class WidgetSchema(Schema):
        id = fields.Integer(as_string=True)
        name = fields.String(required=True)
        description = fields.String()

    return {"widget": WidgetSchema()}


@pytest.fixture
def make_app(app, models, schemas):
    def maker(config):
        app.config.update(config)

        # Register custom shell context
        def shell_context_processor():
            return {
                "shellctx": "shellctx-value",
                "shellctx_overriden_by_context": "not-overridden",
            }

        app.shell_context_processor(shell_context_processor)

        return app

    return maker


@pytest.fixture(scope="session")
def runner():
    return CliRunner()


@pytest.fixture
def run_command(runner, make_app):
    def run(args=tuple(), *, config=None, **kwargs):
        app = make_app(config=config or {})
        obj = ScriptInfo(create_app=lambda: app)
        # Always use default python shell
        return runner.invoke(cli, ("--shell", "py", *args), obj=obj, **kwargs)

    return run


# -----------------------------------------------------------------------------


def test_no_args(run_command):
    result = run_command()
    assert result.exit_code == 0
    # Flask imports
    assert "Flask:" in result.output
    assert "app, db, g" in result.output
    # Models
    assert "Models:" in result.output
    # Schemas
    assert "Schemas:" in result.output
    assert "WidgetSchema" in result.output


def test_additional_context(run_command):
    result = run_command(
        config={
            "RESTY_SHELL_CONTEXT": {"foo": "foo-value", "bar": "bar-value"}
        },
        input="bar",
    )
    assert "Additional:" in result.output
    assert "bar, foo" in result.output
    assert ">>> 'bar-value'" in result.output


def test_flask_shell_context_processors(run_command):
    result = run_command(
        config={
            "RESTY_SHELL_CONTEXT": {
                "shellctx_overriden_by_context": "overridden-in-settings"
            }
        },
        input="shellctx\nshellctx_overriden_by_context",
    )
    assert "Flask:" in result.output
    assert ">>> 'shellctx-value'" in result.output
    assert ">>> 'overridden-in-settings'" in result.output


def test_logo(run_command):
    result = run_command(config={"RESTY_SHELL_LOGO": "foobarbaz"})
    assert "foobarbaz" in result.output


def test_prompt(run_command):
    result = run_command(config={"RESTY_SHELL_PROMPT": "foo>>>>"})
    assert "foo>>>>" in result.output


def test_context_format(run_command):
    def format_ctx(ctx, **kwargs):
        return "foobarbaz"

    result = run_command(config={"RESTY_SHELL_CONTEXT_FORMAT": format_ctx})
    assert "foobarbaz" in result.output


def test_shell_setup(run_command):
    def shell_setup(context):
        context["shell_setup_test"] = "foobar"

    result = run_command()
    assert "shell_setup_test" not in result.output

    run_command(config={"RESTY_SHELL_SETUP": shell_setup})

    result = run_command()
    assert "shell_setup_test" in result.output
