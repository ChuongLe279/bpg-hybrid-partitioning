import numpy as np
from scipy.sparse import csr_array


class BregmanProximalGradient():
    def __init__(self, W: csr_array, partitions_num: int = 2, step_size: float = 1.0, iterations_num: int = 50, seed: int = 42):
        self.W = W
        self.partitions_num = partitions_num
        self.step_size = step_size
        self.iterations_num = iterations_num
        self.seed = seed
        self.X: np.ndarray | None = None
        self.labels: np.ndarray | None = None

    # chạy thuật toán bpg (algorithm 1) giải bài toán normalized cut
    def run(self) -> np.ndarray:
        w_dense = self.W.toarray() if hasattr(self.W, 'toarray') else np.array(self.W)
        n = w_dense.shape[0]
        k = self.partitions_num
        w_1n = w_dense.sum(axis=1)

        # bước 1: khởi tạo ma trận xác suất mềm x ban đầu với chút nhiễu ngẫu nhiên
        np.random.seed(self.seed)
        j = np.ones((n, k))
        r = np.random.uniform(0.0, 1.0, (n, k))
        x = (1.0 / k) * j + 0.1 * r

        # bước 2: chuẩn hóa xác suất mỗi dòng về tổng bằng 1
        eps = 1e-7
        x = x / (x.sum(axis=1, keepdims=True) + eps)

        # bước 3: lặp cập nhật gradient bregman
        for t in range(self.iterations_num):
            g = np.zeros((n, k), dtype=np.float64)
            for i in range(k):
                xi = x[:, i]
                w_xi = w_dense.dot(xi)
                vol = float(xi.dot(w_1n))
                cut = float(xi.dot(w_1n - w_xi))
                num = vol * (w_1n - 2.0 * w_xi) - cut * w_1n
                den = (vol + eps) ** 2
                g[:, i] = num / den

            # bước 7: cập nhật ma trận theo hàm mũ của gradient (thưởng tăng phạt giảm)
            y = x * np.exp(-self.step_size * g)

            # bước 8: chuẩn hóa lại từng dòng về 100% bằng phép chiếu bregman
            x = y / (y.sum(axis=1, keepdims=True) + eps)

        self.X = x
        # bước 10: làm tròn rời rạc, chọn máy chủ có xác suất cao nhất cho mỗi tuple
        self.labels = np.argmax(x, axis=1)
        return self.labels
