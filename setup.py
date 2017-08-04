import os
import imp
import json
from setuptools import setup, find_packages


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


##### building cache
def load_submodule(name):
    """Load submodule without loading rest of the package.

    With this I can load explicit Hamiltonians omitting
    dependency needed by the rest of the package.

    credit goes to HYRY: stackoverflow.com/questions/21298833
    """
    names = name.split(".")
    path = None
    for name in names:
        f, path, info = imp.find_module(name, path)
        path = [path]
    return imp.load_module(name, f, path[0], info)


BASE_DIR = os.path.join( os.path.dirname(os.path.abspath(__file__)), 'semicon')
def build_cache():
    explicit_foreman = load_submodule('semicon.kp_models.explicit_foreman')

    print("building models' cache")
    fname = os.path.join(BASE_DIR, 'kp_models', 'cache.json')
    data = {'foreman': str(explicit_foreman.foreman)}
    with open(fname, 'w') as f:
        json.dump(data, f)


##### standard python build

classifiers = """\
    Development Status :: 3 - Alpha
    Intended Audience :: Science/Research
    Intended Audience :: Developers
    Programming Language :: Python :: 3 :: Only
    Topic :: Software Development
    Topic :: Scientific/Engineering
    Operating System :: POSIX
    Operating System :: Unix"""

setup(
    name="semicon",
    version="0.0.0",

    author='R.J. Skolasinski',
    author_email='r.j.skolasinski@gmail.com',
    description=("Python package for doing k.p simulation"),
    license="BSD",

    long_description=read("README.md"),
    platforms=["Unix", "Linux"],
    url="https://gitlab.kwant-project.org/r-j-skolasinski/semicon",


    packages=find_packages('.'),

    setup_requires=['sympy >= 0.7.6'],
    install_requires=['kwant >= 1.3', 'sympy >= 0.7.6', 'pandas >= 0.19.2'],
    classifiers=[c.strip() for c in classifiers.split('\n')]
)


build_cache()
