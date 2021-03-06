from setuptools import setup, find_packages
from pytatki import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='Pytatki',
    version=__version__,
    description="Organizer klasowy",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Patryk Niedźwiedziński",
    author_email="pniedzwiedzinski19@gmail.com",
    url="https://github.com/PRD-ev/pytatki",
    packages=find_packages(),
    tests_require=['pytest', 'pytest-flask'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ]
    )
