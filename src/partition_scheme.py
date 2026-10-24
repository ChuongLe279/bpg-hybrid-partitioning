from __future__ import annotations
import random
from faker import Faker
import networkx as nx


"""Class cốt lõi"""
class PartitionScheme():
    def __init__(self, heat_graph: nx.Graph, partitions: dict[int, set[int]]):
        self.heat_graph = heat_graph
        self.partitions = partitions


class CreatePartitionScheme():
    """dữ liệu giả, sau này sẽ chuyển thành hàm Database -> Partitioning Scheme"""
    def __init__(self, num_records: int = 10, seed: int = 42):
        self.num_records = num_records
        self.seed = seed
        self.fake = Faker()
        Faker.seed(seed)
        random.seed(seed)
        self.data: list[dict] = []
        self.transactions: list[dict] = []
        self.heat_graph: nx.Graph | None = None

    # mock database, thông tin các khách hàng, mỗi người có mã số ID, tên, email, số điện thoại, số dư tiền
    def generate_mock_data(self) -> list[dict]:
        self.data = []
        for i in range(1, self.num_records + 1):
            record = {
                'id': i,
                'name': self.fake.name(),
                'email': self.fake.email(),
                'phone': self.fake.phone_number(),
                'city': self.fake.city(),
                'balance': round(float(self.fake.random_number(digits=5)), 2)
            }
            self.data.append(record)
        return self.data

    # hàm này tạo nhật ký người dùng truy cập, đại khái là vậy
    # ví dụ thao tác người dùng bấm trên web/app
    #
    # ý nghĩa của bảng này là nó ghi lại xem những ai hay được truy cập cùng nhau trong các giao dịch.
    # Thuật toán của chúng ta sẽ nhìn vào bảng này để gom những người hay giao dịch chung về cùng một máy chủ,
    # nhằm triệt tiêu tối đa các giao dịch phân tán làm chậm hệ thống
    def generate_mock_transactions(self, num_transactions: int = 10) -> list[dict]:
        if not self.data:
            self.generate_mock_data()

        self.transactions = []
        half = max(1, self.num_records // 2)
        group_1 = [r['id'] for r in self.data if r['id'] <= half]
        group_2 = [r['id'] for r in self.data if r['id'] > half]

        tx_id = 1
        # cluster 1 transactions
        for _ in range(num_transactions // 2):
            ops = []
            attrs = ['name', 'email'] if random.random() < 0.6 else ['balance']
            picked_ids = random.sample(group_1, min(2, len(group_1)))
            for pid in picked_ids:
                ops.append({'tuple_id': pid, 'attrs': attrs})
            self.transactions.append({'tx_id': tx_id, 'ops': ops})
            tx_id += 1

        # cluster 2 transactions
        for _ in range(max(1, num_transactions // 2 - 1)):
            ops = []
            attrs = ['name', 'email'] if random.random() < 0.6 else ['balance']
            picked_ids = random.sample(group_2, min(2, len(group_2)))
            for pid in picked_ids:
                ops.append({'tuple_id': pid, 'attrs': attrs})
            self.transactions.append({'tx_id': tx_id, 'ops': ops})
            tx_id += 1

        # giả sử có 5 người, chia ra 2 nhóm
        # đoạn code dưới lấy ngẫu nhiên 1 người nhóm 1 và 1 người nhóm 2 nhét chung vào 1 giao dịch, tạo ra giao dịch bắc cầu
        # 2 nhóm này đại diện cho 2 node trong hệ thống phân tán
        # nếu như giao dịch chỉ xảy ra trong 1 nhóm mà (tức là trong 1 node) thì bài toán có gì để xử lý nữa đâu
        if group_1 and group_2:
            self.transactions.append({
                'tx_id': tx_id,
                'ops': [
                    {'tuple_id': random.choice(group_1), 'attrs': ['name', 'email']},
                    {'tuple_id': random.choice(group_2), 'attrs': ['name', 'email']}
                ]
            })

        return self.transactions

    """
    Số đỉnh trên đồ thị: Quyết định bởi số tuple và số loại cột được đọc (phân mảnh dọc)
    Số Node / Site phân tán: Là số máy chủ mà ta muốn chia
    Dù hệ thống có 2 máy chủ hay 10 máy chủ, nếu dữ liệu chỉ bị đọc theo 2 loại cột thì 5 người vẫn chỉ sinh ra đúng 10 đỉnh trên đồ thị nhiệt

    giả sử có 5 người giao dịch với mỗi cụm 2 giao dịch
    đồ thị nhiệt sẽ tạo ra 10 đỉnh
    tương tự nếu có 3 loại phép chiều thì 15
    """
    def build_heat_graph(self) -> nx.Graph:
        if not self.transactions:
            self.generate_mock_transactions()

        # đếm tần suất truy cập cho mỗi tuple projection
        # mỗi tuple projection là một đỉnh trên đồ thị nhiệt
        node_access_counts: dict[tuple[int, tuple[str, ...]], int] = {}
        co_access_counts: dict[tuple[tuple[int, tuple[str, ...]], tuple[int, tuple[str, ...]]], int] = {}

        for tx in self.transactions:
            tx_nodes = []
            for op in tx['ops']:
                t_id = op['tuple_id']
                attrs = tuple(sorted(op['attrs']))
                key = (t_id, attrs)
                node_access_counts[key] = node_access_counts.get(key, 0) + 1
                if key not in tx_nodes:
                    tx_nodes.append(key)

            # đếm tần suất truy cập đồng thời giữa các tuple projection khác nhau trong cùng một giao dịch
            # mỗi cặp tuple projection khác nhau có cùng được truy cập trong 1 giao dịch sẽ tạo thành 1 cạnh
            for i in range(len(tx_nodes)):
                for j in range(i + 1, len(tx_nodes)):
                    pair = tuple(sorted([tx_nodes[i], tx_nodes[j]]))
                    co_access_counts[pair] = co_access_counts.get(pair, 0) + 1

        heat_graph = nx.Graph()
        key_to_id: dict[tuple[int, tuple[str, ...]], int] = {}
        node_id_counter = 1

        # in ra bảng heat graph vertical (đồ thị nhiệt đỉnh)
        # thêm các đỉnh với trọng số nhiệt
        for key in sorted(node_access_counts.keys()):
            key_to_id[key] = node_id_counter
            t_id, attrs = key
            heat_graph.add_node(
                node_id_counter,
                tuple_id=t_id,
                table='customers',
                attrs=list(attrs),
                weight=float(node_access_counts[key])
            )
            node_id_counter += 1

        # in ra bảng heat graph edges (đồ thị nhiệt cạnh)
        # thêm các cạnh với trọng số nhiệt
        for (k1, k2), count in co_access_counts.items():
            u = key_to_id[k1]
            v = key_to_id[k2]
            heat_graph.add_edge(u, v, weight=float(count))

        # thêm cạnh projection dọc cho các tuple giống nhau
        # các cạnh này không có trọng số
        # hai mảnh này là thông tin của cùng 1 người, trọng số bằng 0 để báo cho thuật toán biết 2 phần là của cùng 1 người
        tuple_groups: dict[int, list[int]] = {}
        for key, node_id in key_to_id.items():
            t_id, _ = key
            tuple_groups.setdefault(t_id, []).append(node_id)

        for t_id, group in tuple_groups.items():
            if len(group) > 1:
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        u = group[i]
                        v = group[j]
                        if not heat_graph.has_edge(u, v):
                            heat_graph.add_edge(u, v, weight=0.0)

        self.heat_graph = heat_graph
        return heat_graph

    def run(self) -> PartitionScheme:
        graph = self.build_heat_graph()
        initial_partitions = {0: set(graph.nodes())}
        return PartitionScheme(graph, initial_partitions)
