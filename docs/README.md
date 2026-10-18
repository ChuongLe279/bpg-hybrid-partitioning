## Chuẩn bị

1. Vì sao chưa nên đụng vào TPC-C lúc này?

TPC-C quá phức tạp để debug: TPC-C có tới 9 bảng liên kết chặt chẽ (Warehouse, District, Customer, Orders...) và 5 loại transaction phức tạp. Nếu thuật toán phân mảnh chạy ra kết quả lạ, ta sẽ không biết lỗi do công thức BPG, do cách tạo đồ thị nhiệt, hay do logic nghiệp vụ rắc rối của TPC-C\
Khó kiểm soát kết quả mong đợi: Với TPC-C, số lượng dữ liệu và giao dịch rất lớn, rất khó để ta nhẩm bằng mắt xem thuật toán chia như vậy đã tối ưu hay chưa\
Tốn tài nguyên và thời gian setup: Cài đặt benchmark chuẩn đòi hỏi nhiều cấu hình môi trường, làm chậm tiến độ hoàn thiện khung thuật toán chính

2. Lợi thế khi dùng faker tạo Mock Data

Biết trước kết quả mong đợi (Ground Truth): Ta hoàn toàn có thể "gài bẫy" dữ liệu để kiểm thử thuật toán. Ví dụ:\
Nhóm transaction 1: Thường xuyên truy cập chung các khách hàng từ ID 1 đến 50 (cùng cụm)\
Nhóm transaction 2: Thường xuyên truy cập chung các khách hàng từ ID 51 đến 100 (cùng cụm)\
Nếu BPG chia đúng, nó bắt buộc phải gom nhóm 1 vào Site A và nhóm 2 vào Site B. Điều này giúp ta kiểm chứng ngay công thức BPG chạy đúng hay sai\
Dễ dàng kiểm thử phân mảnh dọc (Vertical Partitioning): Với bảng đơn giản gồm (id, name, email, phone, address, balance):\
Một số transaction chỉ xem (id, name, email)\
Một số transaction chỉ tính toán (id, balance)\
Đây chính là nguyên liệu hoàn hảo để tạo các đỉnh projection khác nhau của cùng 1 tuple nối với nhau bằng cạnh trọng số 0 trên Heat Graph\

3. Bản chất của 2 thứ chúng ta cần làm

Quy trình dữ liệu giả lập sẽ đi qua 3 nấc:

Mock Database:

Dùng faker sinh ra một bảng đơn giản (ví dụ tầm 50 đến 100 dòng)\
Lưu trữ dưới dạng bảng hoặc dictionary dữ liệu thông thường\
Mock Transactions (Workload Generator):\

Một transaction bản chất là một danh sách các thao tác: "Đọc dòng nào, trên những cột nào"\
Ví dụ: Transaction_1 = [(tuple_1, ['name', 'email']), (tuple_2, ['name', 'email'])]\
Từ Transaction biến thành Heat Graph (Mục 6):\

Đếm tần suất: tuple nào được gọi nhiều lần thì tăng độ nóng\
Cặp tuple nào cùng xuất hiện trong một transaction thì nối cạnh có trọng số cộng dồn\
Hai projection của cùng 1 tuple thì nối cạnh trọng số 0\
Từ Transaction biến thành Ma trận BPG (Mục 7):

Ma trận kề W: Chứa trọng số truy cập đồng thời giữa các thực thể dữ liệu\
Ma trận khởi tạo X: Trạng thái phân bổ ban đầu cho $k$ phân vùng

File [src/create_partition_scheme.py](../src/create_partition_scheme.py) có nhiệm vụ tạo mock data\
Sau đó ta triển khai first partitioning ([src/first_partitioning.py](../src/first_partitioning.py))

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

=> Đọc [partition_scheme_bpg.md](partition_scheme_bpg.md) để hiểu ma trận W

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
