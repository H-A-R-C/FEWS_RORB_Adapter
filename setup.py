from pathlib import Path
from setuptools import setup, find_packages

DESCRIPTION = (
    "Tooling"
)
APP_ROOT = Path(__file__).parent
README = (APP_ROOT / "README.md").read_text()
AUTHOR = "Yanni Wang"
AUTHOR_EMAIL = "yanni.wangh@harc.com.au"
PROJECT_URLS = {
    "Documentation": "",
    "Bug Tracker": "",
    "Source Code": "https://github.com/Yanni-HARC/RORB-FEWS-adapter.git",
}
INSTALL_REQUIRES = [
    "pandas == 2.2.3",
    "numpy == 2.0.2",
    "lxml == 5.3.0",
    'netCDF4 == 1.7.2',
    "packaging == 24.1",
]
EXTRAS_REQUIRE = {
    "dev": [
        "pytest",
        "pyinstaller"
    ]
}
__version__ = "0.0.1"
setup(
    name="fews_rorb_adapter",
    description=DESCRIPTION,
    long_description=README,
    long_description_content_type="text/markdown",
    version=__version__,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    maintainer=AUTHOR,
    maintainer_email=AUTHOR_EMAIL,
    license="MIT",
    url="https://github.com/H-A-R-C/FEWS_RORB_Adapter",
    project_urls=PROJECT_URLS,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
    package_data={"": ["src/rorb_config.json", "src/fews_config.json", "src/file_mapping.json"]},
)