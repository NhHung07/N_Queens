# Nghiên cứu Thực nghiệm SAT Encodings và So sánh Đa Mô hình (SAT, CP, MIP) cho Bài toán N-Queens

**Học phần:** Các vấn đề hiện đại trong Khoa học Máy tính  
**Tác giả:** **Trần Nhật Hưng**  

---

## 📌 Giới thiệu Đề tài

Bài toán **$N$-Queens (Xếp $N$ quân hậu)** là bài toán kinh điển trong Khoa học Máy tính và Trí tuệ Nhân tạo: *Tìm cách đặt $N$ quân hậu trên bàn cờ kích thước $N \times N$ sao cho không có hai quân hậu nào có thể tấn công lẫn nhau* (nghĩa là không cùng hàng, không cùng cột và không cùng đường chéo).

Dự án này tập trung triển khai và đánh giá thực nghiệm chuyên sâu:
1. **5 kỹ thuật mã hóa ràng buộc At-Most-One (AMO) trong SAT Solving:**
   - **Binomial (Pairwise / Cổ điển)**: Đơn giản, $0$ biến phụ, số mệnh đề bùng nổ $O(N^4)$.
   - **Sequential Counter (Sinz 2005)**: Thanh ghi tích lũy tuyến tính, duy trì Arc-Consistency (GAC).
   - **Binary (Bitwise)**: Mã hóa bit nhị phân, tối ưu hóa số biến phụ $O(N \log N)$.
   - **Commander Variable (Klieber & Kwon 2007)**: Phân cấp biến chỉ huy theo nhóm ($g=3$).
   - **2-Product (Chen 2010)**: Phân bố ma trận phụ 2 chiều $p \times q$, biến phụ $O(N^{1.5})$.
   - Bộ giải SAT chính được sử dụng: **PySAT Glucose4** (CDCL với cơ chế quản lý mệnh đề học theo chỉ số Literal Block Distance - LBD).

2. **So sánh Đa Mô hình (Cross-Paradigm Benchmark) giữa 3 trường phái giải chính xác:**
   - **SAT Solving (Logic Mệnh đề):** PySAT Glucose4.
   - **Constraint Programming (CP):** Google OR-Tools (CP-SAT), IBM ILOG CPLEX (CP Optimizer).
   - **Mixed Integer Programming (MIP / 0-1 ILP):** Gurobi Optimizer, IBM ILOG CPLEX (MIP).

---

## 📂 Cấu trúc Thư mục Dự án

```text
N_Queens_2/
├── README.md                      # Tài liệu hướng dẫn dự án
├── requirements.txt               # Danh sách thư viện Python cần thiết
├── src/                           # Mã nguồn triển khai các giải thuật
│   ├── binomial.py                # SAT Solver với Binomial (Pairwise) Encoding
│   ├── sequential.py              # SAT Solver với Sequential Counter Encoding
│   ├── binary.py                  # SAT Solver với Binary (Bitwise) Encoding
│   ├── commander.py               # SAT Solver với Commander Variable Encoding
│   ├── product.py                 # SAT Solver với 2-Product Encoding
│   ├── sat.py                     # CLI điều phối trung tâm cho SAT Solvers
│   ├── cpsat.py                   # Constraint Programming với Google OR-Tools CP-SAT
│   ├── cplex_cp.py                # Constraint Programming với IBM CPLEX CP Optimizer
│   ├── gurobi.py                  # 0-1 MIP với Gurobi Optimizer
│   └── cplex_mip.py               # 0-1 MIP với IBM CPLEX MIP
└── results/                       # Thực nghiệm, Dữ liệu và Trực quan hóa
    ├── benchmark/                 # Kịch bản tự động hóa đo đạc thực nghiệm
    │   ├── encoding.py            # Benchmark so sánh 5 phương pháp SAT Encoding
    │   └── solver.py              # Benchmark so sánh 5 Solvers (SAT, CP, MIP)
    ├── data/                      # Dữ liệu thực nghiệm dạng CSV
    │   ├── encoding.csv           # Dữ liệu thực nghiệm Encodings (N=4 đến N=128)
    │   └── solver.csv             # Dữ liệu thực nghiệm Solvers (N=4 đến N=150)
    ├── figures/                   # Thư mục lưu trữ biểu đồ xuất bản (Publication figures)
    └── visualization/             # Jupyter Notebooks phân tích và trực quan hóa
        ├── encoding.ipynb         # Phân tích chuyên sâu về SAT Encodings
        └── solver.ipynb           # So sánh đối đầu SAT (Glucose4) vs CP vs MIP
```

---

## ⚙️ Cài đặt Môi trường (Installation)

### 1. Khởi tạo môi trường ảo Python
Khuyến nghị sử dụng Python 3.10 trở lên:

```bash
# Tạo môi trường ảo
python3 -m venv .venv

# Kích hoạt môi trường ảo
source .venv/bin/activate  # Trên Linux / macOS
# .venv\Scripts\activate   # Trên Windows
```

### 2. Cài đặt các thư viện phụ thuộc
Cài đặt toàn bộ dependencies qua `requirements.txt`:

```bash
pip install -r requirements.txt
```

> **Lưu ý về Solvers & Bản quyền:**
> - **PySAT (Glucose4)** và **Google OR-Tools** là thư viện mã nguồn mở, hoạt động không giới hạn kích thước bài toán.
> - **IBM CPLEX (MIP & CP Optimizer):** Khi cài đặt bản quyền học thuật đầy đủ (**IBM ILOG CPLEX Optimization Studio**), nâng cấp môi trường ảo thông qua lệnh:
>   ```bash
>   docplex config --upgrade <Đường_dẫn_cài_đặt_CPLEX_Studio>
>   ```
>   Sau khi nâng cấp, CPLEX sẽ mở khóa toàn bộ sức mạnh, không còn giới hạn 1000 biến nhị phân và giải mượt mà lên tới $N = 200+$!
> - **Gurobi Optimizer:** Đã kích hoạt bản quyền học thuật đầy đủ (**Gurobi Academic License** qua `grbgetkey`), mở khóa toàn bộ giới hạn số biến nhị phân để giải mượt mà trên các kích thước $N$ lớn.

---

## 🚀 Hướng dẫn Sử dụng (Usage & Quickstart)

### 1. Giải bài toán N-Queens bằng SAT Solvers (CLI)
Sử dụng file điều phối `src/sat.py` để giải và in trực quan bàn cờ nghiệm:

```bash
# Giải bài toán 8-Queens bằng Sequential Counter Encoding (Glucose4)
python src/sat.py -n 8 -e sequential

# Giải bài toán 12-Queens bằng Binary Encoding
python src/sat.py -n 12 -e binary

# Giải bài toán bằng Commander Variable Encoding
python src/sat.py -n 10 -e commander
```

### 2. Chạy thử nghiệm các Solver khác
```bash
# Giải bằng Google OR-Tools CP-SAT (Ràng buộc AllDifferent)
python src/cpsat.py

# Giải bằng Gurobi MIP (0-1 Linear Programming)
python src/gurobi.py -n 12

# Giải bằng IBM CPLEX CP Optimizer
python src/cplex_cp.py

# Giải bằng IBM CPLEX MIP
python src/cplex_mip.py
```

### 3. Tự động hóa Đo đạc Thực nghiệm (Benchmarks)
Các script trong `results/benchmark/` tự động chạy thực nghiệm và cập nhật số liệu trực tiếp vào `results/data/`:

```bash
# Đo đạc 5 phương pháp SAT Encoding từ N=4 đến N=128
python results/benchmark/encoding.py --n_list 4 8 16 32 64 128

# Đo đạc so sánh 5 Solvers (SAT Glucose4, CP-SAT, CPLEX CP, Gurobi, CPLEX MIP)
python results/benchmark/solver.py --n_list 4 8 12 16 20 24 28 30 40 50 100 150
```

### 4. Khám phá Trực quan hóa & Phân tích (Jupyter Notebooks)
Khởi chạy Jupyter Notebook để xem các phân tích chi tiết, bảng thống kê và biểu đồ độ phân giải cao:

```bash
jupyter notebook results/visualization/encoding.ipynb
jupyter notebook results/visualization/solver.ipynb
```

---

## 📊 Tóm tắt Kết quả Thực nghiệm Chính

### 1. So sánh các Kỹ thuật SAT Encoding (trên Glucose4)

| Kỹ thuật Encoding | Biến phụ ($m$ biến) | Mệnh đề CNF ($m$ biến) | Tổng Mệnh đề N-Queens | Đánh giá Thực nghiệm |
| :--- | :---: | :---: | :---: | :--- |
| **Binomial (Pairwise)** | $0$ | $O(m^2)$ | $O(N^4)$ | Nhanh ở $N \le 20$; bùng nổ bộ nhớ khi $N > 64$ ($428.864$ mệnh đề tại $N=64$, tự động SKIP ở $N \ge 80$). |
| **Sequential Counter** | $O(m)$ | $O(m)$ | $O(N^2)$ | Duy trì Arc-Consistency mạnh mẽ; tốc độ giải ổn định ở $N \le 128$ ($52.89$s); chạm ngưỡng timeout ở $N \ge 150$. |
| **Binary (Bitwise)** | $O(\log m)$ | $O(m \log m)$ | $O(N^2 \log N)$ | **Quán quân SAT solving trên Glucose4 ở $N$ lớn** (tại $N=128$ mất $0.24$s, $N=500$ chỉ mất **$3.99$ giây**). |
| **Commander Variable** | $O(m/g)$ | $O(m)$ | $O(N^2)$ | Cân bằng tốt giữa số lượng mệnh đề và biến phụ ($g=3$), nhanh nhất ở $N \le 200$ (tại $N=200$ chỉ mất **$0.45$ giây**). |
| **2-Product** | $O(\sqrt{m})$ | $O(m)$ | $O(N^2)$ | Cấu trúc ma trận 2D hiệu quả, giải tốt đến $N=150$ ($22.05$ giây), chạm ngưỡng timeout ở $N \ge 200$. |

### 2. So sánh Đa Mô hình: SAT (Glucose4) vs CP vs MIP (Quy mô lên đến N = 1000)

1. **Ở miền kích thước nhỏ và vừa ($N \le 30$):**
   - **Gurobi (MIP)** giải cực nhanh ở các ma trận nhỏ nhờ cơ chế Presolve và Simplex khởi tạo tốt ($0.001 - 0.004$ giây).
   - **PySAT (Glucose4)** và **OR-Tools (CP-SAT)** duy trì thời gian giải dưới $0.03$ giây.
   - **IBM CPLEX (CP)** giải ổn định trong khoảng $0.008 - 0.010$ giây.

2. **Ở miền kích thước trung bình và lớn ($N = 40 \to 250$):**
   - **Gurobi (MIP)** (Academic License) mở khóa toàn bộ sức mạnh, giải $N = 100$ trong $0.033$ giây, $N = 200$ trong $0.118$ giây, $N = 250$ trong $0.194$ giây.
   - **IBM CPLEX (MIP)** (Academic License) giải $N = 200$ trong $0.523$ giây, $N = 250$ trong $0.875$ giây.
   - **Google OR-Tools (CP-SAT)** giải $N = 250$ trong $10.29$ giây, nhưng bắt đầu chạm ngưỡng timeout ở $N \ge 300$.
   - **PySAT (Glucose4)** giải thành công đến $N = 200$ ($150.9$ giây), chạm ngưỡng timeout khi $N \ge 250$ do số biến và mệnh đề bùng nổ hàng triệu.

3. **Ở miền quy mô cực lớn ($N = 300 \to 1000$):**
   - **IBM CPLEX (CP)** thể hiện sức mạnh vượt trội và áp đảo toàn diện: Nhờ cấu hình $N$ biến nguyên và 3 ràng buộc toàn cục `AllDifferent` cùng cơ chế lan truyền miền giá trị mạnh mẽ, giải thành công $N = 1000$ chỉ trong **$0.236$ giây**!
   - **IBM CPLEX (MIP)** giải thành công cả bàn cờ $N = 1000$ ($1.000.000$ biến nhị phân) trong **$19.01$ giây**.
   - **Gurobi (MIP)** giải mượt mà đến $N = 900$ ($810.000$ biến nhị phân) trong **$15.66$ giây**, chạm ngưỡng thời gian 120s ở $N = 1000$.
   - **CP-SAT** và **PySAT Glucose4** chạm ngưỡng thời gian (TIMEOUT) do hạn chế trong việc tìm nghiệm feasible đầu tiên trên miền tìm kiếm quá rộng hoặc bùng nổ mệnh đề CNF.



