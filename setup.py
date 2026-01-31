"""
Weyland Filament Tool
Setup configuration
"""

from setuptools import setup, find_packages

setup(
    name="weyland-filament-tool",
    version="1.0.0",
    description="Research and generate Bambu Studio filament profiles",
    author="Weyland-Yutani Corporation - Advanced Materials Division",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "selenium>=4.15.0",
        "lxml>=4.9.0",
        "pandas>=2.1.0",
        "python-dotenv>=1.0.0",
        "jsonschema>=4.19.0",
        "pyyaml>=6.0.1",
    ],
    entry_points={
        "console_scripts": [
            "bambu-filament=main:main",
        ],
    },
)
