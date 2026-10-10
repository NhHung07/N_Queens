"""
Giải bài toán N-Queens bằng SAT Solver với phương pháp mã hóa Binary (Bitwise).

Mô hình hóa SAT Encoding:
- Biến quyết định: x[i, j] in {1, ..., n^2} đại diện cho việc đặt hậu tại ô (i, j).
- Phương pháp AMO: Binary Encoding (sử dụng ceil(log2(m)) biến bit phụ).
- Ràng buộc 1 (Hàng): Mỗi hàng có đúng 1 quân hậu (Exactly-One).
- Ràng buộc 2 (Cột): Mỗi cột có đúng 1 quân hậu (Exactly-One).
- Ràng buộc 3 (Đường chéo chính): Mỗi đường chéo chính có tối đa 1 quân hậu (At-Most-One).
- Ràng buộc 4 (Đường chéo phụ): Mỗi đường chéo phụ có tối đa 1 quân hậu (At-Most-One).
"""

import math
import time
from pysat.solvers import Minisat22


class VarManager:
    """Quản lý và cấp phát ID cho các biến phụ mới."""

    def __init__(self, start_id=1):
        self.current_id = start_id

    def get_new_variables(self, length):
        vars_list = list(range(self.current_id, self.current_id + length))
        self.current_id += length
        return vars_list

    @property
    def total_vars(self):
        return self.current_id - 1


def generate_variables(n):
    """Khởi tạo ma trận biến bàn cờ N x N (ID từ 1 đến N^2)."""
    return [[i * n + j + 1 for j in range(n)] for i in range(n)]


def at_most_one(clauses, variables, var_manager):
    """
    Ràng buộc At-Most-One (AMO) bằng mã hóa nhị phân (Binary / Bitwise Encoding):
    - Gán mỗi biến một mã nhị phân có ceil(log2(m)) bit.
    - Nếu 1 biến nhận True thì các biến bit phụ phải khớp với biểu diễn nhị phân của nó.
    """
    m = len(variables)
    if m <= 1:
        return

    # Số lượng bit nhị phân cần dùng
    num_bits = math.ceil(math.log2(m))
    if num_bits == 0:
        return

    # Cấp phát các biến phụ đại diện cho từng bit
    bit_vars = var_manager.get_new_variables(num_bits)

    # Nếu biến thứ i nhận True -> các biến bit phụ phải khớp với mã nhị phân của i
    for i, var in enumerate(variables):
        for bit_idx in range(num_bits):
            bit_val = (i >> bit_idx) & 1
            lit = bit_vars[bit_idx] if bit_val == 1 else -bit_vars[bit_idx]
            clauses.append([-var, lit])


def exactly_one(clauses, variables, var_manager):
    """Ràng buộc Exactly-One (EO): gồm At-Least-One (ALO) và At-Most-One (AMO)."""
    clauses.append(variables)
    at_most_one(clauses, variables, var_manager)


def generate_clauses(n, variables, var_manager):
    """Sinh toàn bộ các mệnh đề CNF cho bài toán N-Queens."""
    clauses = []

    # 1. Ràng buộc hàng: mỗi hàng có đúng 1 quân hậu
    for i in range(n):
        exactly_one(clauses, variables[i], var_manager)

    # 2. Ràng buộc cột: mỗi cột có đúng 1 quân hậu
    for j in range(n):
        exactly_one(clauses, [variables[i][j] for i in range(n)], var_manager)

    # 3. Ràng buộc đường chéo phụ (hướng lên - sang phải: i + j = const)
    for i in range(1, n):
        diagonal = []
        row = i
        col = 0
        while row >= 0 and col < n:
            diagonal.append(variables[row][col])
            row -= 1
            col += 1
        at_most_one(clauses, diagonal, var_manager)

    for j in range(1, n - 1):
        diagonal = []
        row = n - 1
        col = j
        while row >= 0 and col < n:
            diagonal.append(variables[row][col])
            row -= 1
            col += 1
        at_most_one(clauses, diagonal, var_manager)

    # 4. Ràng buộc đường chéo chính (hướng xuống - sang phải: i - j = const)
    for i in range(n - 1):
        diagonal = []
        row = i
        col = 0
        while row < n and col < n:
            diagonal.append(variables[row][col])
            row += 1
            col += 1
        at_most_one(clauses, diagonal, var_manager)

    for j in range(1, n - 1):
        diagonal = []
        row = 0
        col = j
        while row < n and col < n:
            diagonal.append(variables[row][col])
            row += 1
            col += 1
        at_most_one(clauses, diagonal, var_manager)

    return clauses


def solve_n_queens(n):
    """Giải bài toán N-Queens bằng SAT Solver (Minisat22)."""
    start_time = time.time()
    variables = generate_variables(n)
    var_manager = VarManager(start_id=n * n + 1)
    clauses = generate_clauses(n, variables, var_manager)
    total_vars = var_manager.total_vars

    # Khởi tạo bộ giải Minisat22 và nạp các mệnh đề CNF
    solver = Minisat22()
    for clause in clauses:
        solver.add_clause(clause)

    sat = solver.solve()
    elapsed_time = time.time() - start_time

    # Trích xuất ma trận nghiệm dạng bàn cờ 2D
    solution = None
    if sat:
        model = solver.get_model()
        solution = [[int(model[i * n + j] > 0) for j in range(n)] for i in range(n)]

    solver.delete()

    return {
        "solution": solution,
        "n": n,
        "variables": total_vars,
        "clauses": len(clauses),
        "time": elapsed_time,
        "sat": sat
    }


def print_solution(result):
    """Hiển thị thông tin kết quả giải và trực quan hóa bàn cờ."""
    if result is None:
        print("Không tìm thấy lời giải.")
        return

    if isinstance(result, dict):
        solution = result.get("solution")
        print(f"--- N-Queens SAT (Binary Encoding) ---")
        print(f"Kích thước bàn cờ (N): {result.get('n')}")
        print(f"Trạng thái            : {'SAT (Tìm thấy lời giải)' if result.get('sat') else 'UNSAT'}")
        print(f"Số biến               : {result.get('variables')}")
        print(f"Số mệnh đề            : {result.get('clauses')}")
        print(f"Thời gian giải        : {result.get('time'):.4f} giây")
    else:
        solution = result

    if solution is None:
        print("Không tìm thấy lời giải.")
    else:
        if result.get("n", 0) <= 20:
            print("Trực quan bàn cờ (Q = Hậu, . = Trống):")
            for row in solution:
                print(" ".join("Q" if cell else "." for cell in row))
        else:
            print(f"(Bàn cờ kích thước N={result.get('n')} quá lớn để hiển thị chi tiết)")


if __name__ == "__main__":
    n = 8
    result = solve_n_queens(n)
    print_solution(result)
