import networkx as nx
import numpy as np
from scipy.sparse import csr_array
import first_partitioning as fp
from create_partition_scheme import CreatePartitionScheme
from partition_scheme_bpg import PartitionScheme_BPG
from bpg import BregmanProximalGradient
from bpg_partition_scheme import BPG_PartitionScheme

"""class cốt lõi"""
class PartitionScheme():
    def __init__(self, heat_graph: nx.Graph, partitions: dict[int, set[int]]):
        self.heat_graph = heat_graph
        self.partitions = partitions


class PartitioningUnbalancedGraph(): # Algorithm 3
    def __init__(self, heat_graph: nx.Graph, partition_scheme: PartitionScheme, site_num: int):
        self.heat_graph = heat_graph
        self.partition_scheme = partition_scheme
        self.site_num = site_num

    def run(self):
        return self.heat_graph

class PartitioningMinimumCutGraph(): # Algorithm 4
    def __init__(self, heat_graph: nx.Graph, partition_scheme: PartitionScheme, site_num: int, depth_search: int):
        self.heat_graph = heat_graph
        self.partition_scheme = partition_scheme
        self.site_num = site_num
        self.depth_search = depth_search

    def run(self):
        return self.heat_graph



'''
hệ thống chia làm 3 trường hợp:

Case 1: Hệ thống mất cân bằng tải -> gọi Algorithm 3
Case 2: Có quá nhiều transaction phân tán (nhiều critical edges) -> gọi Algorithm 4
Case 3: Hệ thống ban đầu chưa được phân mảnh (chỉ có 1 partition duy nhất) -> gọi Algorithm 5 (First Partitioning) để tạo ra phương án phân mảnh khởi đầu cho k node (site)
'''
class Partitioning(): # Algorithm 2
    def __init__(self, heat_graph: nx.Graph, site_num: int, workload_factor: float, distributed_percentage: float):
        self.heat_graph = heat_graph
        self.site_num = site_num
        self.workload_factor = workload_factor
        self.distributed_percentage = distributed_percentage

    def run(self):
        return self.heat_graph

