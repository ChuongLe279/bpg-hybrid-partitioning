### Vai trò của `PartitionScheme_BPG`

Ma trận đuợc sinh ra cũng giống giống ma trận Use trong môn CSDL Phân Tán vậy, chỉ khác nó là ma trận ái lực, bài báo dùng ma trận đưa vào mô hình đồ thị tối ưu rồi dùng thuật toán gradient BPG để giải

Thuật toán BPG (trong bài báo 2) là thuật toán tối ưu toán học, nó **không hiểu khái niệm node hay edge của networkx**. Nó chỉ hiểu một thứ duy nhất: **Ma trận đại số tuyến tính**

Vì vậy, class `PartitionScheme_BPG` đóng vai trò là "người phiên dịch":
- Nhận vào `PartitionScheme`
- Gom cụm các mẩu dữ liệu của cùng 1 tuple lại với nhau (để đảm bảo không bị xé lẻ một người sang 2 máy)
- Chuyển toàn bộ các mối liên hệ giao dịch thành **Ma trận kề W** (kích thước 5x5, tương ứng với 5 khách hàng)

---

### Kết quả ma trận W được sinh ra:

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

### Nhìn vào ma trận W, bạn sẽ thấy ngay bức tranh toán học:
- **T1 và T2**: Có số liên kết cực lớn là **5.0** (cặp bạn thân 1)
- **T4 và T5**: Có số liên kết lớn là **3.0** (cặp bạn thân 2)
- **T3**: Đóng vai trò là cây cầu nối (nối với T1 trọng số 1.0 và T5 trọng số 1.0)

Khi ma trận W này được đưa vào BPG ở **Bước 2**, các phép tính ma trận của BPG sẽ nhìn thấy ngay 2 cụm khổng lồ này và gom `[T1, T2]` về 1 bên, `[T4, T5]` về 1 bên
