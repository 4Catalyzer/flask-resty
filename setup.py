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
    version='0.21.0',
    description="Building blocks for REST APIs for Flask",
    url='https://github.com/4Catalyzer/flask-resty',
    author="Jimmy Jia",
    author_email='tesrin@gmail.com',
    license='MIT',
    python_requires='>=3.5',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Framework :: Flask',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
    keywords='rest flask',
    packages=('flask_resty',),
    install_requires=(
        'Flask >= 1.0',
        'Flask-SQLAlchemy >= 1.0',
        'marshmallow >= 2.2.0',
        'SQLAlchemy >= 1.0.0',
        'Werkzeug >= 0.11',
    ),
    extras_require={
        'jwt': ('PyJWT >= 1.4.0', 'cryptography >= 2.0.0'),
        'tests': (
            'coverage',
            'flake8',
            'flake8-config-4catalyzer',
            'psycopg2-binary',
            'pytest',
        ),
    },
    cmdclass={
        'clean': system('rm -rf build dist *.egg-info'),
        'package': system('python setup.py pandoc sdist bdist_wheel'),
        'pandoc': system('pandoc README.md -o README.rst'),
        'publish': system('twine upload dist/*'),
        'release': system('python setup.py clean package publish'),
        'test': system('tox'),
    },
    entry_points={
        "pytest11": ("flask-resty = flask_resty.testing",),
    },
)
