from setuptools import setup, find_packages

setup(
    name="privacy-fl-kds",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=["tenseal", "vantage6-algorithm-tools", "cryptography"],
)
