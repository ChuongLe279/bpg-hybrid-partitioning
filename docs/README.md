# Kiến trúc hệ thống và phân bố thuật toán

Tài liệu này tổng hợp cấu trúc thư mục mã nguồn cùng bảng ánh xạ chi tiết 8 thuật toán từ hai bài báo nghiên cứu

---

### 1. Cấu trúc project

Các class đã được gom nhóm khoa học theo chức năng thay vì để mỗi class một file rời rạc hay dồn 800 dòng vào một chỗ:

- [src/core.py](../src/core.py): Chứa cấu trúc dữ liệu dùng chung `PartitionScheme`
- [src/workload.py](../src/workload.py): Chứa dữ liệu mẫu và bộ sinh Heat Graph (`CreatePartitionScheme`)
- [src/baseline.py](../src/baseline.py): Chứa thuật toán khởi tạo tham chiếu Algorithm 5 (`FirstPartitioning`)
- [src/bpg.py](../src/bpg.py): Chứa trọn bộ pipeline thuật toán BPG (`PartitionScheme_BPG`, `BregmanProximalGradient`, `BPG_PartitionScheme`, `bpg_partition`)
- [src/dynamic.py](../src/dynamic.py): Chứa cụm thuật toán điều phối động của Chương (Algorithm 2 `Partitioning`, Algorithm 3 `PartitioningUnbalancedGraph`, Algorithm 4 `PartitioningMinimumCutGraph`)
- [src/main.py](../src/main.py): Đóng gói import và export để gọi dùng thuận tiện
- [src/test.py](../src/test.py): Kịch bản chạy thử nghiệm kiểm tra kết quả giữa Algorithm 5 và BPG

---

### 2. Danh mục đầy đủ 8 thuật toán của cả hai bài báo

| STT | Tên thuật toán                                 | Vị trí cài đặt                                                      | Thuộc bài báo     | Vai trò và nhiệm vụ                                                         |
| --- | ---------------------------------------------- | ------------------------------------------------------------------- | ----------------- | --------------------------------------------------------------------------- |
| 1   | Khởi tạo đồ thị nhiệt Heat Graph               | [src/workload.py](../src/workload.py) (`CreatePartitionScheme`)     | Autonomous NewSQL | Biến workload giao dịch thành đồ thị phân mảnh hỗn hợp                      |
| 2   | Thuật toán khởi tạo cơ sở Algorithm 5          | [src/baseline.py](../src/baseline.py) (`FirstPartitioning`)         | Autonomous NewSQL | Phân mảnh ban đầu theo phương pháp tham lam (baseline để đối chiếu)         |
| 3   | Chuyển đổi đồ thị sang ma trận ái lực $W$      | [src/bpg.py](../src/bpg.py) (`PartitionScheme_BPG`)                 | BPG NCut          | Coarsening các projection của cùng tuple thành ma trận kề $W$               |
| 4   | Bộ giải Bregman Proximal Gradient              | [src/bpg.py](../src/bpg.py) (`BregmanProximalGradient`)             | BPG NCut          | Giải bài toán tối ưu Normalized Cut bằng cập nhật hàm mũ                    |
| 5   | Rời rạc hóa ma trận $X$ về PartitionScheme     | [src/bpg.py](../src/bpg.py) (`BPG_PartitionScheme`)                 | BPG NCut          | Chuyển ma trận xác suất mềm $X$ thành gán nhãn cứng cho từng máy chủ        |
| 6   | Điều phối phân mảnh thích ứng động Algorithm 2 | [src/dynamic.py](../src/dynamic.py) (`Partitioning`)                | Autonomous NewSQL | Giám sát độ lệch tải và chi phí giao dịch phân tán trong lúc chạy           |
| 7   | Tái cân bằng tải lệch Algorithm 3              | [src/dynamic.py](../src/dynamic.py) (`PartitioningUnbalancedGraph`) | Autonomous NewSQL | Tìm tuple đại diện và di chuyển cụm 2 bước (2-hops) để giảm tải             |
| 8   | Tối ưu cắt cạnh và bản sao Algorithm 4         | [src/dynamic.py](../src/dynamic.py) (`PartitioningMinimumCutGraph`) | Autonomous NewSQL | Triệt tiêu cạnh cắt nóng nhất bằng di chuyển hoặc tạo bản sao (Replication) |

---

### 3. Luồng dữ liệu xuyên suốt hệ thống

```
Faker Mock DB -> Mock Transactions
                      |
                      v
      [src/workload.py] CreatePartitionScheme
              (Sinh đồ thị Heat Graph)
                      |
                      v
        +-------------+-------------+
        |                           |
        v                           v
[src/baseline.py]            [src/bpg.py]
FirstPartitioning (Algo 5)    PartitionScheme_BPG (Tạo W)
        |                           |
        |                           v
        |                    BregmanProximalGradient (Giải X)
        |                           |
        |                           v
        |                    BPG_PartitionScheme (Rời rạc hóa)
        |                           |
        +-------------+-------------+
                      |
                      v
              PartitionScheme
                      |
                      v
      [src/dynamic.py] Partitioning (Algo 2)
        |
        +---> Lệch tải quá mức: Gọi Algo 3 (PartitioningUnbalancedGraph)
        |
        +---> Vết cắt quá lớn: Gọi Algo 4 (PartitioningMinimumCutGraph)
```

---

## Chuẩn bị

### 1. Vì sao chưa nên đụng vào TPC-C lúc này?

- **TPC-C quá phức tạp để debug**: TPC-C có tới 9 bảng liên kết chặt chẽ (Warehouse, District, Customer, Orders...) và 5 loại transaction phức tạp. Nếu thuật toán phân mảnh chạy ra kết quả lạ, ta sẽ không biết lỗi do công thức BPG, do cách tạo đồ thị nhiệt, hay do logic nghiệp vụ rắc rối của TPC-C
- **Khó kiểm soát kết quả mong đợi**: Với TPC-C, số lượng dữ liệu và giao dịch rất lớn, rất khó để ta nhẩm bằng mắt xem thuật toán chia như vậy đã tối ưu hay chưa
- **Tốn tài nguyên và thời gian setup**: Cài đặt benchmark chuẩn đòi hỏi nhiều cấu hình môi trường, làm chậm tiến độ hoàn thiện khung thuật toán chính

### 2. Lợi thế khi dùng Faker tạo Mock Data

- **Biết trước kết quả mong đợi (Ground Truth)**: Ta hoàn toàn có thể "gài bẫy" dữ liệu để kiểm thử thuật toán:
  + Nhóm transaction 1: Thường xuyên truy cập chung các khách hàng từ ID 1 đến 50 (cùng cụm)
  + Nhóm transaction 2: Thường xuyên truy cập chung các khách hàng từ ID 51 đến 100 (cùng cụm)
  + Nếu BPG chia đúng, nó bắt buộc phải gom nhóm 1 vào Site A và nhóm 2 vào Site B. Điều này giúp ta kiểm chứng ngay công thức BPG chạy đúng hay sai
- **Dễ dàng kiểm thử phân mảnh dọc (Vertical Partitioning)**: Với bảng đơn giản gồm (id, name, email, phone, address, balance):
  + Một số transaction chỉ xem (id, name, email)
  + Một số transaction chỉ tính toán (id, balance)
  + Đây chính là nguyên liệu hoàn hảo để tạo các đỉnh projection khác nhau của cùng 1 tuple nối với nhau bằng cạnh trọng số 0 trên Heat Graph

### 3. Bản chất của 2 thứ chúng ta cần làm

Quy trình dữ liệu giả lập sẽ đi qua các nấc:

**A. Mock Database**:
- Dùng Faker sinh ra một bảng đơn giản (ví dụ tầm 50 đến 100 dòng)
- Lưu trữ dưới dạng bảng hoặc dictionary dữ liệu thông thường

**B. Mock Transactions (Workload Generator)**:
- Một transaction bản chất là một danh sách các thao tác: "Đọc dòng nào, trên những cột nào"
- Ví dụ: `Transaction_1 = [(tuple_1, ['name', 'email']), (tuple_2, ['name', 'email'])]`

**C. Từ Transaction biến thành Heat Graph (Mục 6)**:
- Đồ thị nhiệt $G = (V, E)$:
  + Mỗi đỉnh $v \in V$ đại diện cho một tuple projection với trọng số nhiệt $\omega(v)$ là tần suất truy cập
  + Cạnh có trọng số $w = 0$: nối các projection của cùng một tuple (để bảo toàn dữ liệu một người)
  + Cạnh có trọng số $w > 0$: nối các tuple cùng xuất hiện trong một transaction (cộng dồn tần suất truy cập đồng thời)

**D. Từ Transaction biến thành Ma trận BPG (Mục 7)**:

1. **Ma trận kề ái lực $W \in \mathbb{R}^{N \times N}$**: Đo tần suất truy cập đồng thời giữa các thực thể dữ liệu:

$$W_{ij} = \sum_{T \in \mathcal{T}} \mathbb{I}(i \in T \text{ và } j \in T)$$

2. **Ma trận phân bổ xác suất $X \in \mathbb{R}^{N \times K}$**: Trạng thái phân bổ ban đầu cho $K$ phân vùng (máy chủ):

$$X = [x_{ij}]_{N \times K}, \quad \text{với } \sum_{j=1}^K x_{ij} = 1, \; \forall i \in \{1, \dots, N\}$$





## Test:

```sh
just test
```

hoặc

```sh
python src/test.py
```

## Output:

```sh
=== MOCK DATABASE (CUSTOMERS) ===
+----+------------------+----------------------------+------------------------+---------------+-----------+
| ID |       Name       |           Email            |         Phone          |      City     |  Balance  |
+----+------------------+----------------------------+------------------------+---------------+-----------+
| 1  |   Allison Hill   |  donaldgarcia@example.net  |    +1-219-560-0133     | Robinsonshire | 36,463.00 |
| 2  | Abigail Shaffer  |   jpeterson@example.org    | 001-851-316-1559x40781 |   Mariastad   | 75,674.00 |
| 3  | Benjamin Stanley |    tracie31@example.com    |    575-425-5341x928    |    Grayside   | 28,785.00 |
| 4  |  Sarah Parsons   | lydiatrujillo@example.com  |    513-695-3767x242    |   Hurstfurt   | 47,447.00 |
| 5  |  Zachary Hicks   | camposmichelle@example.org |  +1-326-691-6697x8480  | Danielchester | 20,730.00 |
+----+------------------+----------------------------+------------------------+---------------+-----------+

=== MOCK TRANSACTIONS ===
+-------+------------------------------------------------------+
| Tx ID |         Operations (Tuple ID -> Attributes)          |
+-------+------------------------------------------------------+
|   1   |       Tuple 1 ['balance'], Tuple 2 ['balance']       |
|   2   | Tuple 1 ['name', 'email'], Tuple 2 ['name', 'email'] |
|   3   |       Tuple 1 ['balance'], Tuple 2 ['balance']       |
|   4   | Tuple 1 ['name', 'email'], Tuple 2 ['name', 'email'] |
|   5   | Tuple 1 ['name', 'email'], Tuple 2 ['name', 'email'] |
|   6   |       Tuple 5 ['balance'], Tuple 4 ['balance']       |
|   7   | Tuple 5 ['name', 'email'], Tuple 4 ['name', 'email'] |
|   8   |       Tuple 3 ['balance'], Tuple 5 ['balance']       |
|   9   |       Tuple 4 ['balance'], Tuple 5 ['balance']       |
|   10  | Tuple 1 ['name', 'email'], Tuple 3 ['name', 'email'] |
+-------+------------------------------------------------------+

=== HEAT GRAPH VERTICES ===
+---------+----------+--------------------+---------------+
| Node ID | Tuple ID | Projection (Attrs) | Heat (Weight) |
+---------+----------+--------------------+---------------+
|    1    |    1     |    ['balance']     |      2.0      |
|    2    |    1     | ['email', 'name']  |      4.0      |
|    3    |    2     |    ['balance']     |      2.0      |
|    4    |    2     | ['email', 'name']  |      3.0      |
|    5    |    3     |    ['balance']     |      1.0      |
|    6    |    3     | ['email', 'name']  |      1.0      |
|    7    |    4     |    ['balance']     |      2.0      |
|    8    |    4     | ['email', 'name']  |      1.0      |
|    9    |    5     |    ['balance']     |      3.0      |
|    10   |    5     | ['email', 'name']  |      1.0      |
+---------+----------+--------------------+---------------+

=== HEAT GRAPH EDGES ===
+--------------+--------+----------------------------------+
| Edge (u - v) | Weight |            Edge Type             |
+--------------+--------+----------------------------------+
|    1 - 3     |  2.0   |      Co-access transaction       |
|    1 - 2     |  0.0   | Vertical projection (same tuple) |
|    2 - 4     |  3.0   |      Co-access transaction       |
|    2 - 6     |  1.0   |      Co-access transaction       |
|    3 - 4     |  0.0   | Vertical projection (same tuple) |
|    5 - 9     |  1.0   |      Co-access transaction       |
|    5 - 6     |  0.0   | Vertical projection (same tuple) |
|    7 - 9     |  2.0   |      Co-access transaction       |
|    7 - 8     |  0.0   | Vertical projection (same tuple) |
|    8 - 10    |  1.0   |      Co-access transaction       |
|    9 - 10    |  0.0   | Vertical projection (same tuple) |
+--------------+--------+----------------------------------+

=== INITIAL PARTITION SCHEME (BEFORE ALGORITHM 5) ===
Total partitions: 1
Partition 0: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] # --> ban đầu chỉ có 1 partition, TRẠNG THÁI BAN ĐẦU KHI CHƯA PHÂN MẢNH GÌ CẢ, dồn hết vào 1 máy chủ

=== PARTITION SCHEME (AFTER FIRST PARTITIONING - ALGORITHM 5) ===
# First partition (algo 5) hoặc sau này thay bằng BPG sẽ chia đều ra các node
Total partitions: 2
+-----------+---------------------+-----------------+----------------+
| Partition |   Nodes (Vertices)  | Tuples Included | Total Workload |
+-----------+---------------------+-----------------+----------------+
|   Site 0  |     [1, 2, 5, 6]    |      [1, 3]     |      8.0       | # --> Gồm các node 1, 2, 5, 6 và các tuple 1, 3
|   Site 1  | [3, 4, 7, 8, 9, 10] |    [2, 4, 5]    |      12.0      | # --> Gồm các node 3, 4, 7, 8, 9, 10 và các tuple 2, 4, 5
+-----------+---------------------+-----------------+----------------+

=== CRITICAL EDGES (DISTRIBUTED TRANSACTIONS) ===
+-----------------------+-----------+---------+-------------------+
| Critical Edge (u - v) | From Site | To Site | Weight (Overhead) |
+-----------------------+-----------+---------+-------------------+
|         1 - 3         |   Site 0  |  Site 1 |        2.0        | # --> Các giao dịch giữa node 1 và node 3
|         2 - 4         |   Site 0  |  Site 1 |        3.0        | # --> Các giao dịch giữa node 2 và node 4
|         5 - 9         |   Site 0  |  Site 1 |        1.0        | # --> Các giao dịch giữa node 5 và node 9
+-----------------------+-----------+---------+-------------------+
Total distributed transaction cost (Cut Weight): 6.0 # --> Tổng chi phí giao dịch phân tán
```

=> Tới đây hãy đọc [first_partitioning.md](first_partitioning.md) để hiểu thêm nhược điểm của cách này

```sh
=== BPG AFFINITY MATRIX W (AFTER COARSENING) ===
+-------------------------+-----+-----+-----+-----+-----+
|     Coarsened Tuple     |  T1 |  T2 |  T3 |  T4 |  T5 |
+-------------------------+-----+-----+-----+-----+-----+
|  Tuple 1 (Nodes [1, 2]) | 0.0 | 5.0 | 1.0 | 0.0 | 0.0 |
|  Tuple 2 (Nodes [3, 4]) | 5.0 | 0.0 | 0.0 | 0.0 | 0.0 |
|  Tuple 3 (Nodes [5, 6]) | 1.0 | 0.0 | 0.0 | 0.0 | 1.0 |
|  Tuple 4 (Nodes [8, 7]) | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 |
| Tuple 5 (Nodes [9, 10]) | 0.0 | 0.0 | 1.0 | 3.0 | 0.0 |
+-------------------------+-----+-----+-----+-----+-----+
```

=> Đọc [partition_scheme_bpg.md](partition_scheme_bpg.md) để hiểu ma trận ái lực $W$

```sh
=== BPG SOFT ASSIGNMENT MATRIX X ===
+-----------------+-----------+-----------+--------------------+
| Coarsened Tuple | P(Site 0) | P(Site 1) | Assigned Partition |
+-----------------+-----------+-----------+--------------------+
|     Tuple 1     |   1.0000  |   0.0000  |       Site 0       |
|     Tuple 2     |   1.0000  |   0.0000  |       Site 0       |
|     Tuple 3     |   0.3225  |   0.6775  |       Site 1       |
|     Tuple 4     |   0.0000  |   1.0000  |       Site 1       |
|     Tuple 5     |   0.0000  |   1.0000  |       Site 1       |
+-----------------+-----------+-----------+--------------------+

=== PARTITION SCHEME (AFTER BPG ALGORITHM) ===
Total partitions: 2
+-----------+---------------------+-----------------+----------------+
| Partition |   Nodes (Vertices)  | Tuples Included | Total Workload |
+-----------+---------------------+-----------------+----------------+
|   Site 0  |     [1, 2, 3, 4]    |      [1, 2]     |      11.0      |
|   Site 1  | [5, 6, 7, 8, 9, 10] |    [3, 4, 5]    |      9.0       |
+-----------+---------------------+-----------------+----------------+

=== BPG CRITICAL EDGES (DISTRIBUTED TRANSACTIONS) ===
+-----------------------+-----------+---------+-------------------+
| Critical Edge (u - v) | From Site | To Site | Weight (Overhead) |
+-----------------------+-----------+---------+-------------------+
|         2 - 6         |   Site 0  |  Site 1 |        1.0        |
+-----------------------+-----------+---------+-------------------+
BPG distributed transaction cost (Cut Weight): 1.0

=== COMPARISON: ALGORITHM 5 VS BPG ===
+-------------------------------------+-------------------------+----------------------+
|              Criterion              |   Algorithm 5 (Greedy)  | BPG (Normalized Cut) |
+-------------------------------------+-------------------------+----------------------+
|           Site 0 Workload           |        8.0 (40%)        |      11.0 (55%)      |
|           Site 1 Workload           |        12.0 (60%)       |      9.0 (45%)       |
|       Number of Critical Edges      | 3 edges (1-3, 2-4, 5-9) |     1 edge (2-6)     |
| Total Cut Weight (Network Overhead) |           6.0           |         1.0          |
|          Overhead Reduction         |         Baseline        |        -83.3%        |
+-------------------------------------+-------------------------+----------------------+
```

=> Đọc [bpg.md](bpg.md) để hiểu chi tiết thuật toán BPG


## Tài liệu liên quan

- [docs/first_partitioning.md](first_partitioning.md): Phân tích chi tiết Algorithm 5 và nguyên nhân gây nghẽn mạng
- [docs/partition_scheme_bpg.md](partition_scheme_bpg.md): Giải thích ma trận ái lực $W$ và quá trình gom cụm
- [docs/bpg.md](bpg.md): Công thức toán học và nguyên lý thuật toán BPG
