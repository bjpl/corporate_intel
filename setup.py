"""Setup script for Corporate Intelligence Platform.

This setup.py enables editable installation via: pip install -e .
Modern projects should primarily use pyproject.toml, but setup.py
is provided for compatibility and editable installs.
"""

from pathlib import Path
from setuptools import setup, find_packages

# Read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="corporate-intel",
    version="0.1.0",
    description="Production-hardened corporate intelligence platform for EdTech analysis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Brandon Lambert",
    author_email="brandon.lambert87@gmail.com",
    url="https://github.com/bjpl/corporate_intel",
    license="MIT",

    # Package discovery
    packages=find_packages(where=".", include=["src*"]),
    package_dir={"": "."},

    # Python version requirement
    python_requires=">=3.10",

    # Dependencies are now managed in pyproject.toml
    # This ensures single source of truth
    install_requires=[],  # Defined in pyproject.toml

    # Entry points for CLI commands
    entry_points={
        "console_scripts": [
            "corporate-intel=src.api.main:main",
        ],
    },

    # Package data
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.sql"],
    },

    # Classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],

    # Additional metadata
    keywords="corporate intelligence edtech analytics financial data",
    project_urls={
        "Bug Reports": "https://github.com/bjpl/corporate_intel/issues",
        "Source": "https://github.com/bjpl/corporate_intel",
    },
)
