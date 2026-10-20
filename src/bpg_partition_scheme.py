from __future__ import annotations
import networkx as nx
import numpy as np


class BPG_PartitionScheme():
    def __init__(self, heat_graph: nx.Graph, labels: np.ndarray, coarse_to_nodes: dict[int, list[int]] | None = None):
        self.heat_graph = heat_graph
        self.labels = labels
        self.coarse_to_nodes = coarse_to_nodes

    # chuyển nhãn phân cụm của bpg ngược lại thành PartitionScheme
    def run(self) -> PartitionScheme:
        from main import PartitionScheme
        partitions: dict[int, set[int]] = {}
        for idx, cluster_id in enumerate(self.labels):
            p = int(cluster_id)
            if p not in partitions:
                partitions[p] = set()
            if self.coarse_to_nodes:
                orig_nodes = self.coarse_to_nodes[idx]
                partitions[p].update(orig_nodes)
            else:
                partitions[p].add(idx + 1)
        return PartitionScheme(self.heat_graph, partitions)
