### Vai trò của `PartitionScheme_BPG`

Ma trận được sinh ra có nét tương đồng với ma trận USE trong môn Hệ cơ sở dữ liệu phân tán, nhưng đây là ma trận ái lực (Affinity Matrix) đo mức độ truy cập đồng thời giữa các tuple
Mô hình toán học của bài báo sẽ nhận ma trận này để giải bài toán phân cụm đồ thị bằng thuật toán Bregman Proximal Gradient (BPG)

Thuật toán BPG không nhận trực tiếp cấu trúc đồ thị dạng node và edge của NetworkX, mà nhận đầu vào là **Ma trận kề trọng số $W$**

Class `PartitionScheme_BPG` đóng vai trò là cầu nối:
- Nhận vào `PartitionScheme`
- Gom cụm các mẩu dữ liệu của cùng một tuple lại với nhau (để đảm bảo không bị xé lẻ một người sang hai máy chủ)
- Chuyển toàn bộ các mối liên hệ giao dịch thành **Ma trận kề $W$** (kích thước $5 \times 5$, tương ứng với 5 khách hàng)

---

### Công thức tính ma trận ái lực $W$
Với mỗi cặp tuple $i$ và $j$:

$$W_{ij} = \sum_{T \in \mathcal{T}} \mathbb{I}(i \in T \text{ và } j \in T)$$

Trong đó:
- $\mathcal{T}$ là tập hợp các transaction trong log
- $\mathbb{I}(\dots)$ bằng 1 nếu cả hai tuple cùng xuất hiện trong transaction $T$, ngược lại bằng 0
- Khi coarsening, trọng số $W_{ij}$ là tổng trọng số của tất cả các cạnh nối giữa các mảnh của tuple $i$ và tuple $j$

Dạng ma trận số học:

$$W = \begin{bmatrix}
0.0 & 5.0 & 1.0 & 0.0 & 0.0 \\
5.0 & 0.0 & 0.0 & 0.0 & 0.0 \\
1.0 & 0.0 & 0.0 & 0.0 & 1.0 \\
0.0 & 0.0 & 0.0 & 0.0 & 3.0 \\
0.0 & 0.0 & 1.0 & 3.0 & 0.0
\end{bmatrix}$$

---

### Kết quả ma trận $W$ hiển thị trong bảng:

```text
=== BPG ADJACENCY MATRIX (W) ===
Matrix shape: (5, 5)
+---------+-----+-----+-----+-----+-----+
|  Tuples |  T1 |  T2 |  T3 |  T4 |  T5 |
+---------+-----+-----+-----+-----+-----+
| Tuple 1 | 0.0 | 5.0 | 1.0 | 0.0 | 0.0 |
| Tuple 2 | 5.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Tuple 3 | 1.0 | 0.0 | 0.0 | 0.0 | 1.0 |
| Tuple 4 | 0.0 | 0.0 | 0.0 | 0.0 | 3.0 |
| Tuple 5 | 0.0 | 0.0 | 1.0 | 3.0 | 0.0 |
+---------+-----+-----+-----+-----+-----+
```

### Ý nghĩa toán học từ ma trận $W$:
- **$T_1$ và $T_2$**: Có liên kết ái lực cực mạnh là **5.0** (cặp bạn thân 1)
- **$T_4$ và $T_5$**: Có liên kết ái lực mạnh là **3.0** (cặp bạn thân 2)
- **$T_3$**: Đóng vai trò là cây cầu nối nhỏ (liên kết với $T_1$ trọng số 1.0 và $T_5$ trọng số 1.0)

Khi ma trận $W$ này được đưa vào BPG, thuật toán sẽ nhận diện ngay 2 cụm liên kết chặt chẽ này và gom $[T_1, T_2]$ về một bên, $[T_4, T_5]$ về một bên
