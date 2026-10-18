import networkx as nx
import numpy as np
from scipy.sparse import csr_array


class PartitionScheme_BPG():
    def __init__(self, partition_scheme, use_coarsening: bool = True):
        self.partition_scheme = partition_scheme
        self.heat_graph = partition_scheme.heat_graph
        self.use_coarsening = use_coarsening
        self.node_to_idx: dict[int, int] = {}
        self.idx_to_node: dict[int, int] = {}
        self.coarse_to_nodes: dict[int, list[int]] = {}
        self.W: csr_array | None = None

    # chuyển đồ thị nhiệt thành ma trận kề thưa w
    def run(self) -> csr_array:
        if self.use_coarsening:
            # gom các mảnh thuộc tính của cùng một tuple lại với nhau
            zero_graph = nx.Graph()
            zero_graph.add_nodes_from(self.heat_graph.nodes(data=True))
            for u, v, d in self.heat_graph.edges(data=True):
                if float(d.get('weight', 0.0)) == 0.0:
                    zero_graph.add_edge(u, v)

            coarse_g = nx.Graph()
            node_to_coarse: dict[int, int] = {}
            for c_idx, comp in enumerate(nx.connected_components(zero_graph)):
                members = list(comp)
                self.coarse_to_nodes[c_idx] = members
                coarse_g.add_node(c_idx)
                for n in members:
                    node_to_coarse[n] = c_idx

            # cộng dồn trọng số giao dịch giữa các tuple sau khi gộp
            for u, v, d in self.heat_graph.edges(data=True):
                w = float(d.get('weight', 0.0))
                if w > 0.0:
                    cu, cv = node_to_coarse[u], node_to_coarse[v]
                    if cu != cv:
                        cur_w = float(coarse_g.get_edge_data(cu, cv, {}).get('weight', 0.0))
                        coarse_g.add_edge(cu, cv, weight=cur_w + w)

            nodes = sorted(list(coarse_g.nodes()))
            self.node_to_idx = {n: i for i, n in enumerate(nodes)}
            self.idx_to_node = {i: n for i, n in enumerate(nodes)}
            n_nodes = len(nodes)
            w_mat = np.zeros((n_nodes, n_nodes), dtype=np.float64)
            for u, v, d in coarse_g.edges(data=True):
                i, j = self.node_to_idx[u], self.node_to_idx[v]
                w_mat[i, j] = d.get('weight', 1.0)
                w_mat[j, i] = d.get('weight', 1.0)

            self.W = csr_array(w_mat)
            return self.W
        else:
            # chuyển đổi trực tiếp không qua bước gộp tuple
            nodes = sorted(list(self.heat_graph.nodes()))
            self.node_to_idx = {n: i for i, n in enumerate(nodes)}
            self.idx_to_node = {i: n for i, n in enumerate(nodes)}
            n_nodes = len(nodes)
            w_mat = np.zeros((n_nodes, n_nodes), dtype=np.float64)
            for u, v, d in self.heat_graph.edges(data=True):
                i, j = self.node_to_idx[u], self.node_to_idx[v]
                w = float(d.get('weight', 0.0))
                w_mat[i, j] = w
                w_mat[j, i] = w

            self.W = csr_array(w_mat)
            return self.W
