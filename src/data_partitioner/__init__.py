"""data-partitioner – rebalance uneven data files into uniform partitions."""

from data_partitioner.core import FileFormat, RebalanceResult, rebalance

__all__ = ["FileFormat", "RebalanceResult", "rebalance"]
__version__ = "0.1.0"
