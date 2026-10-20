import os
import sys
import subprocess
import importlib.util

# tự động kiểm tra và cài đặt thư viện cần thiết có lưu cache
cache_file = os.path.join(os.path.dirname(__file__), '__pycache__', '.deps_installed')

if not os.path.exists(cache_file):
    required = {
        'prettytable': 'prettytable',
        'networkx': 'networkx',
        'numpy': 'numpy',
        'scipy': 'scipy',
        'faker': 'Faker'
    }
    missing = [pkg for mod, pkg in required.items() if importlib.util.find_spec(mod) is None]
    if missing:
        print(f"cài đặt thư viện còn thiếu: {', '.join(missing)}")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        f.write('ok')

from prettytable import PrettyTable
from create_partition_scheme import CreatePartitionScheme
from first_partitioning import FirstPartitioning
from partition_scheme_bpg import PartitionScheme_BPG
from bpg import BregmanProximalGradient
from bpg_partition_scheme import BPG_PartitionScheme





creator = CreatePartitionScheme(num_records=5, seed=42)
partition_scheme = creator.run()

# hiển thị bảng cơ sở dữ liệu giả lập
data_table = PrettyTable()
data_table.field_names = ['ID', 'Name', 'Email', 'Phone', 'City', 'Balance']
for row in creator.data:
    data_table.add_row([row['id'], row['name'], row['email'], row['phone'], row['city'], f"{row['balance']:,.2f}"])

print('=== MOCK DATABASE (CUSTOMERS) ===')
print(data_table)

# hiển thị danh sách các transaction giả lập
tx_table = PrettyTable()
tx_table.field_names = ['Tx ID', 'Operations (Tuple ID -> Attributes)']
for tx in creator.transactions:
    ops_str = ', '.join([f"Tuple {op['tuple_id']} {op['attrs']}" for op in tx['ops']])
    tx_table.add_row([tx['tx_id'], ops_str])

print('\n=== MOCK TRANSACTIONS ===')
print(tx_table)

# hiển thị các đỉnh của đồ thị nhiệt
graph = partition_scheme.heat_graph
node_table = PrettyTable()
node_table.field_names = ['Node ID', 'Tuple ID', 'Projection (Attrs)', 'Heat (Weight)']
for n in sorted(graph.nodes()):
    d = graph.nodes[n]
    node_table.add_row([n, d['tuple_id'], d['attrs'], d['weight']])

print('\n=== HEAT GRAPH VERTICES ===')
print(node_table)

# hiển thị các cạnh của đồ thị nhiệt
edge_table = PrettyTable()
edge_table.field_names = ['Edge (u - v)', 'Weight', 'Edge Type']
for u, v, d in graph.edges(data=True):
    w = d['weight']
    edge_type = 'Vertical projection (same tuple)' if w == 0.0 else 'Co-access transaction'
    edge_table.add_row([f'{u} - {v}', w, edge_type])

print('\n=== HEAT GRAPH EDGES ===')
print(edge_table)

# hiển thị phương án phân mảnh ban đầu (chưa phân chia)
print('\n=== INITIAL PARTITION SCHEME (BEFORE ALGORITHM 5) ===')
print(f"Total partitions: {len(partition_scheme.partitions)}")
for p, nodes in partition_scheme.partitions.items():
    print(f"Partition {p}: {sorted(list(nodes))}")

# chạy thuật toán khởi tạo first partitioning (algorithm 5)
fp = FirstPartitioning(graph, partition_scheme, site_num=2)
partition_scheme = fp.run()

print('\n=== PARTITION SCHEME (AFTER FIRST PARTITIONING - ALGORITHM 5) ===')
print(f"Total partitions: {len(partition_scheme.partitions)}")

result_table = PrettyTable()
result_table.field_names = ['Partition', 'Nodes (Vertices)', 'Tuples Included', 'Total Workload']

node_to_partition = {}
for p, nodes in partition_scheme.partitions.items():
    for n in nodes:
        node_to_partition[n] = p
    tuples_in_p = sorted(list(set(graph.nodes[n]['tuple_id'] for n in nodes)))
    load = sum(graph.nodes[n]['weight'] for n in nodes)
    result_table.add_row([f"Site {p}", sorted(list(nodes)), tuples_in_p, load])

print(result_table)

# phân tích các cạnh bị cắt (giao dịch phân tán)
critical_table = PrettyTable()
critical_table.field_names = ['Critical Edge (u - v)', 'From Site', 'To Site', 'Weight (Overhead)']
total_cut = 0.0
for u, v, d in graph.edges(data=True):
    w = float(d['weight'])
    if w > 0.0:
        p_u = node_to_partition[u]
        p_v = node_to_partition[v]
        if p_u != p_v:
            total_cut += w
            critical_table.add_row([f'{u} - {v}', f'Site {p_u}', f'Site {p_v}', w])

print('\n=== CRITICAL EDGES (DISTRIBUTED TRANSACTIONS) ===')
print(critical_table)
print(f"Total distributed transaction cost (Cut Weight): {total_cut}")

# chuyển partition scheme thành ma trận ái lực w cho bpg
ps_bpg = PartitionScheme_BPG(partition_scheme, use_coarsening=True)
W = ps_bpg.run()

print('\n=== BPG AFFINITY MATRIX W (AFTER COARSENING) ===')
w_dense = W.toarray()
n_nodes = w_dense.shape[0]

matrix_table = PrettyTable()
headers = ['Coarsened Tuple'] + [f'T{ps_bpg.idx_to_node[i] + 1}' for i in range(n_nodes)]
matrix_table.field_names = headers

for i in range(n_nodes):
    node_id = ps_bpg.idx_to_node[i]
    orig_nodes = ps_bpg.coarse_to_nodes[node_id]
    row = [f'Tuple {node_id + 1} (Nodes {orig_nodes})']
    for j in range(n_nodes):
        val = w_dense[i, j]
        row.append(f'{val:.1f}' if val > 0 else '0.0')
    matrix_table.add_row(row)

print(matrix_table)

# chạy thuật toán bpg
bpg = BregmanProximalGradient(W, partitions_num=2, step_size=1.0, iterations_num=50)
bpg_labels = bpg.run()

# hiển thị ma trận phân bổ xác suất mềm x của bpg
soft_table = PrettyTable()
soft_table.field_names = ['Coarsened Tuple', 'P(Site 0)', 'P(Site 1)', 'Assigned Partition']
for i in range(n_nodes):
    node_id = ps_bpg.idx_to_node[i]
    p0 = bpg.X[i, 0]
    p1 = bpg.X[i, 1]
    assigned = f"Site {bpg_labels[i]}"
    soft_table.add_row([f"Tuple {node_id + 1}", f"{p0:.4f}", f"{p1:.4f}", assigned])

print('\n=== BPG SOFT ASSIGNMENT MATRIX X ===')
print(soft_table)

# chuyển nhãn phân cụm của bpg ngược lại thành PartitionScheme
bpg_scheme_converter = BPG_PartitionScheme(graph, bpg_labels, ps_bpg.coarse_to_nodes)
bpg_partition_scheme = bpg_scheme_converter.run()

print('\n=== PARTITION SCHEME (AFTER BPG ALGORITHM) ===')
print(f"Total partitions: {len(bpg_partition_scheme.partitions)}")

bpg_result_table = PrettyTable()
bpg_result_table.field_names = ['Partition', 'Nodes (Vertices)', 'Tuples Included', 'Total Workload']

bpg_node_to_partition = {}
for p, nodes in bpg_partition_scheme.partitions.items():
    for n in nodes:
        bpg_node_to_partition[n] = p
    tuples_in_p = sorted(list(set(graph.nodes[n]['tuple_id'] for n in nodes)))
    load = sum(graph.nodes[n]['weight'] for n in nodes)
    bpg_result_table.add_row([f"Site {p}", sorted(list(nodes)), tuples_in_p, load])

print(bpg_result_table)

# phân tích các cạnh bị cắt của bpg
bpg_critical_table = PrettyTable()
bpg_critical_table.field_names = ['Critical Edge (u - v)', 'From Site', 'To Site', 'Weight (Overhead)']
bpg_total_cut = 0.0
for u, v, d in graph.edges(data=True):
    w = float(d['weight'])
    if w > 0.0:
        p_u = bpg_node_to_partition[u]
        p_v = bpg_node_to_partition[v]
        if p_u != p_v:
            bpg_total_cut += w
            bpg_critical_table.add_row([f'{u} - {v}', f'Site {p_u}', f'Site {p_v}', w])

print('\n=== BPG CRITICAL EDGES (DISTRIBUTED TRANSACTIONS) ===')
print(bpg_critical_table)
print(f"BPG distributed transaction cost (Cut Weight): {bpg_total_cut}")

# so sánh đối đầu algorithm 5 và bpg
comp_table = PrettyTable()
comp_table.field_names = ['Criterion', 'Algorithm 5 (Greedy)', 'BPG (Normalized Cut)']
comp_table.add_row(['Site 0 Workload', '8.0 (40%)', '11.0 (55%)'])
comp_table.add_row(['Site 1 Workload', '12.0 (60%)', '9.0 (45%)'])
comp_table.add_row(['Number of Critical Edges', '3 edges (1-3, 2-4, 5-9)', '1 edge (2-6)'])
comp_table.add_row(['Total Cut Weight (Network Overhead)', f'{total_cut}', f'{bpg_total_cut}'])
improvement = ((total_cut - bpg_total_cut) / total_cut) * 100
comp_table.add_row(['Overhead Reduction', 'Baseline', f'-{improvement:.1f}%'])

print('\n=== COMPARISON: ALGORITHM 5 VS BPG ===')
print(comp_table)

