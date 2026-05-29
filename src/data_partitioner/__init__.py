"""data-partitioner – rebalance uneven data files into uniform partitions."""

from data_partitioner.core import FileFormat, RebalanceResult, rebalance
from data_partitioner.streaming import rebalance_streaming

__all__ = ["FileFormat", "RebalanceResult", "rebalance", "rebalance_streaming"]
__version__ = "0.1.0"
