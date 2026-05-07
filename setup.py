from setuptools import find_packages, setup

setup(
    name="data-partitioner",
    version="0.1.0",
    description="Rebalance uneven data files (CSV, Parquet, ORC) into uniformly sized partitions.",
    python_requires=">=3.9",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=["pandas>=1.5", "pyarrow>=12.0"],
    extras_require={"dev": ["pytest>=7.0", "pytest-cov"]},
    entry_points={"console_scripts": ["data-partitioner=data_partitioner.cli:main"]},
)
