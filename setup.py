from setuptools import setup

EXTRAS_REQUIRE = {
    "docs": ("sphinx", "pallets-sphinx-themes"),
    "jwt": ("PyJWT>=1.4.0,<2.0.0", "cryptography>=2.0.0"),
    "tests": ("coverage", "psycopg2-binary", "pytest"),
}
EXTRAS_REQUIRE["dev"] = (
    EXTRAS_REQUIRE["docs"] + EXTRAS_REQUIRE["tests"] + ("tox",)
)

setup(
    name="Flask-RESTy",
    version="1.6.0",
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
        "Flask>=1.1.0",
        "Flask-SQLAlchemy>=1.0",
        "marshmallow>=3.0.0",
        "SQLAlchemy>=1.0.0",
        "Werkzeug>=0.11",
        "konch>=4.0",
    ),
    extras_require=EXTRAS_REQUIRE,
    entry_points={
        "pytest11": ("flask-resty = flask_resty.testing",),
        "flask.commands": ("shell = flask_resty.shell:cli",),
    },
)
