"""
Giải bài toán N-Queens bằng SAT Solver với phương pháp mã hóa Commander Variable (Klieber & Kwon 2007).

Mô hình hóa SAT Encoding:
- Biến quyết định: x[i, j] in {1, ..., n^2} đại diện cho việc đặt hậu tại ô (i, j).
- Phương pháp AMO: Commander Variable (chia nhóm kích thước <= g, dùng biến chỉ huy).
- Ràng buộc 1 (Hàng): Mỗi hàng có đúng 1 quân hậu (Exactly-One).
- Ràng buộc 2 (Cột): Mỗi cột có đúng 1 quân hậu (Exactly-One).
- Ràng buộc 3 (Đường chéo chính): Mỗi đường chéo chính có tối đa 1 quân hậu (At-Most-One).
- Ràng buộc 4 (Đường chéo phụ): Mỗi đường chéo phụ có tối đa 1 quân hậu (At-Most-One).
"""

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


def at_most_one(clauses, variables, var_manager, g=3):
    """
    Ràng buộc At-Most-One (AMO) bằng phương pháp Biến chỉ huy (Commander Variable):
    - Chia tập biến thành các nhóm nhỏ kích thước <= g (mặc định g=3).
    - Mỗi nhóm có 1 biến chỉ huy cmd đại diện cho việc có biến nào trong nhóm nhận True.
    - Đệ quy AMO trên tập các biến chỉ huy.
    - Số mệnh đề: O(m).
    - Số biến phụ: O(m / (g - 1)).
    """
    m = len(variables)
    if m <= 1:
        return

    # Nếu kích thước nhóm nhỏ hơn hoặc bằng g, áp dụng trực tiếp pairwise
    if m <= g:
        for i in range(m):
            for j in range(i + 1, m):
                clauses.append([-variables[i], -variables[j]])
        return

    commanders = []
    for i in range(0, m, g):
        group = variables[i:i + g]
        if len(group) == 1:
            commanders.append(group[0])
            continue

        # Cấp phát biến chỉ huy cmd cho nhóm
        cmd = var_manager.get_new_variables(1)[0]
        commanders.append(cmd)

        # 1. AMO nội bộ trong nhóm: tối đa 1 biến nhận True
        for u in range(len(group)):
            for v in range(u + 1, len(group)):
                clauses.append([-group[u], -group[v]])

        # 2. Nếu có biến trong nhóm True -> cmd phải True: (-u or cmd)
        for u in group:
            clauses.append([-u, cmd])

        # 3. Nếu cmd True -> ít nhất 1 biến trong nhóm True: (-cmd or u_1 or ... or u_g)
        clauses.append([-cmd] + group)

    # Đệ quy áp dụng AMO trên tập các biến chỉ huy
    at_most_one(clauses, commanders, var_manager, g)


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
        print(f"--- N-Queens SAT (Commander Variable Encoding) ---")
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
