# Thuật toán Bregman Proximal Gradient (BPG)

Tài liệu gốc: [BPG.pdf](research/BPG.pdf)

### 1. Ý tưởng cốt lõi của BPG
Ở bước trước, ta đã chuyển PartitionScheme thành ma trận ái lực W kích thước 5x5 (đo độ thân thiết giữa 5 khách hàng)
Thay vì dùng thuật toán tham lam kiểu Algorithm 5, BPG giải bài toán tối ưu phân cụm Normalized Cut (NCut):
- **Tử số**: Cắt ít cạnh có trọng số lớn nhất có thể (mục tiêu: giảm nghẽn mạng)
- **Mẫu số**: Giữ tải giữa các máy chủ cân bằng nhau (mục tiêu: tránh dồn hết việc vào một máy)

---

### 2. Ví dụ trực quan: Cơ chế dịch chuyển xác suất của BPG

<img src="research/formula.png" width=100%>

Công thức toán học trong bài báo (công thức 6):
```text
X^(t+1) = P_c( X^(t) * e^(-lambda * G) )
```

Trong đó:
- **G** chính là ma trận đạo hàm chi phí df/dX
- Dấu `*` (ký hiệu vòng tròn trong ảnh) là phép nhân từng phần tử
- Khi lập trình trên máy tính, thuật toán tách làm 2 bước cho dễ tính:
  1. Tính ruột bên trong ngoặc: `Y = X * e^(-lambda * G)` (tính điểm thưởng / phạt)
  2. Phép chiếu **P_c**: Lấy Y chia cho tổng mỗi dòng để quy về 100% xác suất

Hãy xem ví dụ cụ thể bằng số:

Giả sử một khách hàng ban đầu đang được cân nhắc giữa **Máy A** và **Máy B** với tỉ lệ 50% - 50%:
```text
X = [0.5, 0.5]
```

**Bước 1: Tính độ dốc chi phí (Gradient G)**
- Nếu đưa khách hàng vào **Máy A**: Làm tăng thêm nhiều giao dịch chéo mạng (cost = +2)
- Nếu đưa khách hàng vào **Máy B**: Trùng với các bạn bè hay giao dịch chung (cost = -1)

**Bước 2: Tính điểm thưởng phạt theo hàm số mũ e^(-cost)**
- Máy A bị phạt tụt điểm: e^(-2) = 0.135 (nhỏ hơn 1 nên làm tụt điểm)
- Máy B được thưởng tăng điểm: e^(+1) = 2.718 (lớn hơn 1 nên làm tăng điểm)

**Bước 3: Nhân điểm vào xác suất ban đầu (Y = X * e^(-cost))**
- Điểm tạm thời của Máy A: 0.5 * 0.135 = 0.0675
- Điểm tạm thời của Máy B: 0.5 * 2.718 = 1.359

**Bước 4: Quy về 100% (Phép chiếu chuẩn hóa hàng)**
- Tổng điểm cả 2 máy: 0.0675 + 1.359 = 1.4265
- Tỉ lệ mới của Máy A: 0.0675 / 1.4265 = 4.7%
- Tỉ lệ mới của Máy B: 1.359 / 1.4265 = 95.3%

```text
X_mới = [0.047, 0.953]
```

=> **Ý nghĩa thực tế**:
Ban đầu hệ thống còn phân vân 50% - 50%, nhưng chỉ sau một nhịp tính toán, thuật toán nhận thấy ném dữ liệu vào Máy B ít tốn kém hơn nhiều, nên tỉ lệ tự động dồn 95.3% về Máy B
Cứ lặp như vậy vài vòng, tỉ lệ sẽ dồn hẳn thành 100% về Máy B

---

### 3. So sánh bản chất tư duy: Algorithm 5 vs BPG

| Tiêu chí | Algorithm 5 (Cách cũ của Schreiner) | BPG (Cách mới đề xuất) |
|---|---|---|
| **Triết lý giải thuật** | Tham lam cục bộ (Greedy) | Tối ưu hóa toàn cục (Normalized Cut) |
| **Cách nhìn dữ liệu** | Nhìn từng người một theo thứ tự tải nặng đến nhẹ | Nhìn toàn bộ ma trận ái lực W của toàn hệ thống |
| **Cách xử lý đôi bạn thân** | Thấy Khách 1 và Khách 2 đều bận rộn nên tách đôi ra 2 máy cho đều tải | Nhận ra Khách 1 và Khách 2 liên kết 5.0 cực mạnh nên bắt buộc gom chung vào Site 0 |
| **Xử lý ràng buộc** | Gom cụm thô (coarsening) rồi gán cứng từng hạt giống (seed) | Dùng không gian xác suất mềm liên tục rồi làm tròn rời rạc (Soft to Hard) |
| **Chi phí nghẽn mạng** | Rất cao (**6.0**) do xé nát các giao dịch lớn | Rất thấp (**1.0**) do bảo toàn trọn vẹn các cụm giao dịch nội bộ |
| **Độ cân bằng tải** | Lệch nhiều (Site 0: 40%, Site 1: 60%) | Rất đều (Site 0: 55%, Site 1: 45%) |

---

### 4. Kết quả thực nghiệm đối đầu trên Mock Data

Khi chạy lệnh `just test`, kết quả so sánh số liệu thực tế hiện ra rõ rệt:

```text
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
