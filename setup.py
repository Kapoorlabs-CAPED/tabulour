from setuptools import setup, find_packages

TABULOUR = "tabulour"

with open(f"{TABULOUR}/__init__.py", encoding="utf-8") as f:
    line = next(iter(f))
    VERSION = line.strip().split()[-1][1:-1]

with open("README.md") as f:
    README = f.read()

setup(
    name=TABULOUR,
    version=VERSION,
    description="A table data viewer for Python based on tabulous",
    long_description=README,
    long_description_content_type="text/markdown",
    author="Varun Kapoor, Hanjin Liu",
    author_email="varun.kapoor@kapoorlabs.org",
    license="BSD 3-Clause",
    download_url="https://github.com/Kapoorlabs-CAPED/TABULOUR",
    packages=find_packages(exclude=["docs", "examples", "rst", "tests", "tests.*"]),
    package_data={TABULOUR: ["**/*.pyi", "*.pyi", "**/*.svg", "**/*.png", "**/*.qss"]},
    include_package_data=True,
    install_requires=[
        "magicgui>=0.5.1",
        "psygnal>=0.6.1",
        "qtpy>=1.10.0",
        "pandas>=1.5.2",
        "collections-undo>=0.0.7",
        "appdirs>=1.4.4",
        "qtconsole",
        "qt-command-palette>=0.0.5",
        "toml",
        "matplotlib>=3.1",
        "tabulate",
    ],
    extras_require={
        "all": [
            "seaborn>=0.11",
            "pyqt5>=5.12.3",
            "scipy>=1.7",
            "scikit-learn>=1.1",
        ],
        "pyqt5": ["pyqt5>=5.12.3"],
        "pyqt6": ["pyqt6>=6.3.1"],
        "scikit-learn": ["scikit-learn>=1.0"],
    },
    entry_points={
        "console_scripts": [f"{TABULOUR}={TABULOUR}.__main__:main"],
    },
    python_requires=">=3.8",
)
