from setuptools import setup

setup(
    name="Flask-JSONAPIView",
    version='0.0.0',
    packages=('flask_jsonapiview',),
    install_requires=(
        'Flask',
        'Flask-SQLAlchemy',
        'marshmallow',
        'SQLAlchemy'
    )
)
