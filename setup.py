from setuptools import setup, find_packages

with open("README.rst", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="contrail",
    version="0.0.0",
    packages=find_packages(),
    description="Interface for modeling, generating, visualizing and saving aircraft encounter data sets.",
    long_description=long_description,
    long_description_content_type="text/rst",
    author="Soyeon Jung, Dea Dressel",
    author_email="soyeonj@stanford.edu",
    url="https://github.com/sisl/Contrail`",
    install_requires=[
        "brotli",
        "click",
        "dash",
        "dash-bootstrap-components",
        "dash-core-components",
        "dash-html-components",
        "dash-leaflet",
        "dash-table",
        "Flask",
        "Flask-Compress",
        "geobuf",
        "itsdangerous",
        "Jinja2",
        "MarkupSafe",
        "numpy",
        "pandas",
        "plotly",
        "protobuf",
        "pymap3d",
        "python-dateutil",
        "pytz",
        "scipy",
        "six",
        "tenacity",
        "Werkzeug"
    ],    
    python_requires=">=3.9",
    license="MIT",)