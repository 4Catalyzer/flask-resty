from setuptools import setup

setup(
    name="Flask-JSONAPIView",
    version='0.0.9',
    description="Building blocks for JSON API endpoints for Flask",
    url='https://github.com/4Catalyzer/flask-jsonapiview',
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
        'Topic :: Software Development :: Libraries :: Python Modules'
    ),
    keywords='rest json api flask',
    packages=('flask_jsonapiview',),
    install_requires=(
        'Flask',
        'Flask-SQLAlchemy',
        'marshmallow',
        'SQLAlchemy',
        'Werkzeug'
    )
)
