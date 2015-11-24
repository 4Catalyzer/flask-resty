import os
from setuptools import Command, setup


def system(command):
    class SystemCommand(Command):
        user_options = []

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            os.system(command)

    return SystemCommand


setup(
    name="Flask-RESTy",
    version='0.1.1',
    description="Building blocks for REST APIs for Flask",
    url='https://github.com/4Catalyzer/flask-resty',
    author="Jimmy Jia",
    author_email='tesrin@gmail.com',
    license='MIT',
    classifiers=(
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Flask',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ),
    keywords='rest flask',
    packages=('flask_resty', 'flask_resty.ext'),
    install_requires=(
        'Flask',
        'Flask-SQLAlchemy',
        'marshmallow',
        'SQLAlchemy',
        'Werkzeug',
    ),
    extras_require={
        'jwt': ('PyJWT',),
    },
    cmdclass={
        'pandoc': system('pandoc README.md -o README.rst'),
        'release': system('python setup.py pandoc sdist upload'),
        'test': system('flake8 . && py.test --cov'),
    },
)
