from __future__ import annotations
import networkx as nx
import numpy as np
from scipy.sparse import csr_array
from partition_scheme import PartitionScheme


class PartitionScheme_BPG():
    def __init__(self, partition_scheme: PartitionScheme, use_coarsening: bool = True):
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


class BregmanProximalGradient(): # BPG
    def __init__(self, W: csr_array, partitions_num: int, step_size: float, iterations_num: int):
        self.W = W
        self.partitions_num = partitions_num
        self.step_size = step_size
        self.iterations_num = iterations_num
    
    def run(self) -> np.ndarray:
        rng = np.random.default_rng()
        N = self.W.shape[0] # type: ignore
        K = self.partitions_num
        X = (1 / K) * np.ones((N, K)) + 0.1 * rng.random((N,K))

        # Chuẩn hóa X theo dòng
        X = X / X.sum(axis=1, keepdims=True)

        for t in range(self.iterations_num):
            G = np.empty_like(X)

            for i in range(K):
                # Công thức đạo hàm
                A = (X[:, i] @ (self.W @ np.ones(N))) * (self.W @ np.ones(N) - 2 * (self.W @ X[:, i]))
                B = (X[:, i] @ (self.W @ (np.ones(N) - X[:, i]))) * (self.W @ np.ones(N))
                C = (X[:, i] @ (self.W @ np.ones(N))) ** 2
                C = max(C, 1e-12) # Tránh việc C = 0

                g = (A - B) / C
                G[:, i] = g


            log_Y = np.log(np.maximum(X, 1e-12)) - self.step_size * G
            log_Y -= log_Y.max(axis=1, keepdims=True)

            Y = np.exp(log_Y)
            X = Y / Y.sum(axis=1, keepdims=True)

        return np.argmax(X, axis=1) + 1


class BPG_PartitionScheme():
    def __init__(self, heat_graph: nx.Graph, labels: np.ndarray, coarse_to_nodes: dict[int, list[int]] | None = None):
        self.heat_graph = heat_graph
        self.labels = labels
        self.coarse_to_nodes = coarse_to_nodes

    # chuyển nhãn phân cụm của bpg ngược lại thành PartitionScheme
    def run(self) -> PartitionScheme:
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


def bpg_partition(partition_scheme: PartitionScheme, site_num: int = 2, step_size: float = 1.0, iterations_num: int = 50, seed: int = 42) -> PartitionScheme:
    bpg_prep = PartitionScheme_BPG(partition_scheme, use_coarsening=True)
    W = bpg_prep.run()
    solver = BregmanProximalGradient(W=W, partitions_num=site_num, step_size=step_size, iterations_num=iterations_num)
    labels = solver.run()
    bpg_mapper = BPG_PartitionScheme(partition_scheme.heat_graph, labels, coarse_to_nodes=bpg_prep.coarse_to_nodes)
    return bpg_mapper.run()
