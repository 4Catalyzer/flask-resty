import subprocess

from setuptools import Command, setup

# -----------------------------------------------------------------------------


def system(command):
    class SystemCommand(Command):
        user_options = []

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            subprocess.check_call(command, shell=True)

    return SystemCommand


# -----------------------------------------------------------------------------

setup(
    name="Flask-RESTy",
    version="0.22.1",
    description="Building blocks for REST APIs for Flask",
    url="https://github.com/4Catalyzer/flask-resty",
    author="4Catalyzer",
    author_email="tesrin@gmail.com",
    license="MIT",
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flask",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="rest flask",
    packages=("flask_resty",),
    install_requires=(
        "Flask >= 1.0.3",
        "Flask-SQLAlchemy >= 1.0",
        "marshmallow >= 3.0.0",
        "SQLAlchemy >= 1.0.0",
        "Werkzeug >= 0.11",
    ),
    extras_require={
        "docs": ("sphinx", "pallets-sphinx-themes"),
        "lint": ("pre-commit ~= 1.17"),
        "jwt": ("PyJWT >= 1.4.0", "cryptography >= 2.0.0"),
        "tests": ("coverage", "psycopg2-binary", "pytest"),
    },
    cmdclass={
        "clean": system("rm -rf build dist *.egg-info"),
        "docs": system("make -C docs html"),
        "package": system("python setup.py sdist bdist_wheel"),
        "publish": system("twine upload dist/*"),
        "release": system("python setup.py clean package publish"),
        "test": system("tox"),
    },
    entry_points={"pytest11": ("flask-resty = flask_resty.testing",)},
)
