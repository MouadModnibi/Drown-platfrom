from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="drown",
    version="0.2.4",
    author="Drown Platform",
    author_email="platform@dr0wn.duckdns.org",
    description="CLI tool for managing apps on Drown Platform - a self-hosted PaaS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/drownplatform/drown-cli",
    project_urls={
        "Bug Tracker": "https://github.com/drownplatform/drown-cli/issues",
        "Documentation": "https://github.com/drownplatform/drown-cli#readme",
        "Source Code": "https://github.com/drownplatform/drown-cli",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Build Tools",
        "Topic :: System :: Systems Administration",
    ],
    keywords="drown platform paas cli deployment docker heroku",
    python_requires=">=3.7",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
    ],
    entry_points={
        "console_scripts": [
            "drown=drown.cli:cli",
        ],
    },
)
