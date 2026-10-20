from __future__ import annotations
import networkx as nx


class FirstPartitioning(): # Algorithm 5
    def __init__(self, heat_graph: nx.Graph, partition_scheme: PartitionScheme, site_num: int):
        self.heat_graph = heat_graph
        self.partition_scheme = partition_scheme
        self.site_num = site_num

    # coarsening graph: Gom cụm các đỉnh projection nối nhau bằng cạnh trọng số 0 (thuộc cùng một tuple) thành một đỉnh đại diện với tổng trọng số nhiệt
    # gom cụm các đỉnh thành 1 tập duy nhất, lúc này chỉ cần quản lí theo từng tập, nhiệt của mỗi tập mới bằng tổng nhiệt của các đỉnh cộng lại
    def _coarsening_graph(self) -> tuple[nx.Graph, dict[int, list[int]], dict[int, int]]:
        zero_graph = nx.Graph()
        zero_graph.add_nodes_from(self.heat_graph.nodes(data=True))
        for u, v, d in self.heat_graph.edges(data=True):
            if float(d.get('weight', 0.0)) == 0.0:
                zero_graph.add_edge(u, v)

        coarse_g = nx.Graph()
        node_to_coarse: dict[int, int] = {}
        coarse_to_nodes: dict[int, list[int]] = {}

        for c_idx, comp in enumerate(nx.connected_components(zero_graph)):
            members = list(comp)
            coarse_to_nodes[c_idx] = members
            total_w = sum(float(self.heat_graph.nodes[n].get('weight', 1.0)) for n in members)
            coarse_g.add_node(c_idx, weight=total_w)
            for n in members:
                node_to_coarse[n] = c_idx

        for u, v, d in self.heat_graph.edges(data=True):
            w = float(d.get('weight', 0.0))
            if w > 0.0:
                cu, cv = node_to_coarse[u], node_to_coarse[v]
                if cu != cv:
                    cur_w = float(coarse_g.get_edge_data(cu, cv, {}).get('weight', 0.0))
                    coarse_g.add_edge(cu, cv, weight=cur_w + w)

        return coarse_g, coarse_to_nodes, node_to_coarse

    def run(self):
        coarse_g, coarse_to_nodes, _ = self._coarsening_graph()

        partitions: dict[int, set[int]] = {p: set() for p in range(self.site_num)}
        partition_loads: dict[int, float] = {p: 0.0 for p in range(self.site_num)}
        visited: set[int] = set()

        sorted_nodes = sorted(
            coarse_g.nodes(),
            key=lambda n: (float(coarse_g.nodes[n].get('weight', 1.0)), -n),
            reverse=True
        )

        # Hottest Tuples Seed: Phân bổ lần lượt các đỉnh nóng nhất vào từng partition ban đầu
        # tìm ra các đỉnh nóng nhất, chia đều cho các site, tránh tình trạng 1 site quá tải
        for p in range(min(self.site_num, len(sorted_nodes))):
            node = sorted_nodes[p]
            partitions[p].add(node)
            partition_loads[p] += float(coarse_g.nodes[node].get('weight', 1.0))
            visited.add(node)

        # Remaining Tuples Allocation: Lần lượt duyệt các đỉnh còn lại theo độ nóng giảm dần, chọn partition tối ưu dựa trên tổng trọng số cạnh kết nối và mức độ cân bằng tải
        # Ưu tiên xếp đỉnh vào partition có lực liên kết mạnh nhất để tránh việc transaction bị phân tán giữa các partition
        # Nếu không có liên kết hoặc độ liên kết bằng nhau, thuật toán sẽ chọn partition đang có tổng tải thấp nhất để đảm bảo cân bằng tải theo Equation 1
        for node in sorted_nodes:
            if node in visited:
                continue
            node_w = float(coarse_g.nodes[node].get('weight', 1.0))
            best_p = 0
            best_score = None
            for p in range(self.site_num):
                aff = sum(
                    float(coarse_g[node][nbr].get('weight', 0.0))
                    for nbr in coarse_g.neighbors(node)
                    if nbr in partitions[p]
                )
                score = (aff, -partition_loads[p])
                if best_score is None or score > best_score:
                    best_score = score
                    best_p = p
            partitions[best_p].add(node)
            partition_loads[best_p] += node_w
            visited.add(node)

        # UncoarseningGraph: Bung các đỉnh gom cụm về lại các đỉnh ban đầu trong đồ thị nhiệt
        # và gán nhãn partition tương ứng vào self.partition_scheme.partitions
        final_partitions: dict[int, set[int]] = {p: set() for p in range(self.site_num)}
        for p, c_nodes in partitions.items():
            for cn in c_nodes:
                for orig_node in coarse_to_nodes[cn]:
                    final_partitions[p].add(orig_node)
                    self.heat_graph.nodes[orig_node]['partition'] = p

        self.partition_scheme.partitions = final_partitions
        return self.partition_scheme
