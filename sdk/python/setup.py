"""
Chain Sentinel — Python SDK Setup
"""

from setuptools import setup, find_packages

setup(
    name="chain-sentinel",
    version="1.0.0",
    description="Python SDK for Chain Sentinel — Free token safety scanner across 9 blockchains",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Sentinel",
    author_email="info@chainshieldsentinel.tech",
    url="https://chainshieldsentinel.tech",
    project_urls={
        "Documentation": "https://chainshieldsentinel.tech/docs",
        "Source": "https://github.com/ChainShieldSn/chain-shield",
        "Changelog": "https://chainshieldsentinel.tech/changelog",
    },
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
        "Topic :: Office/Business :: Financial",
    ],
    keywords="crypto blockchain security scanner rugpull honeypot token defi web3",
)
