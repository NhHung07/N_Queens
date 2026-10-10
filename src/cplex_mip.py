"""
Giải bài toán N-Queens bằng IBM ILOG CPLEX (MIP / 0-1 Integer Programming).

Mô hình hóa Mixed Integer Programming (MIP):
- Biến quyết định: x[i, j] in {0, 1} = 1 nếu đặt quân hậu tại ô (i, j).
- Ràng buộc 1 (Hàng): Mỗi hàng có đúng 1 quân hậu -> sum_j x[i, j] == 1
- Ràng buộc 2 (Cột): Mỗi cột có đúng 1 quân hậu -> sum_i x[i, j] == 1
- Ràng buộc 3 (Đường chéo chính): Mỗi đường chéo chính có tối đa 1 quân hậu -> sum x <= 1
- Ràng buộc 4 (Đường chéo phụ): Mỗi đường chéo phụ có tối đa 1 quân hậu -> sum x <= 1
"""

import time
from docplex.mp.model import Model


def solve_n_queens_cplex_mip(n, time_limit=300, threads=8):
    """Giải bài toán N-Queens bằng IBM ILOG CPLEX (MIP)."""
    start_time = time.time()

    # Khởi tạo mô hình CPLEX MIP
    mdl = Model(name="N-Queens-MIP")

    if time_limit is not None:
        mdl.set_time_limit(time_limit)
    if threads is not None:
        mdl.parameters.threads = threads

    # N^2 biến nhị phân x[i, j] in {0, 1}
    x = {(i, j): mdl.binary_var(name=f"x_{i}_{j}") for i in range(n) for j in range(n)}

    # 1. Ràng buộc hàng: mỗi hàng có đúng 1 quân hậu
    for i in range(n):
        mdl.add_constraint(mdl.sum(x[i, j] for j in range(n)) == 1, ctname=f"row_{i}")

    # 2. Ràng buộc cột: mỗi cột có đúng 1 quân hậu
    for j in range(n):
        mdl.add_constraint(mdl.sum(x[i, j] for i in range(n)) == 1, ctname=f"col_{j}")

    # 3. Ràng buộc đường chéo chính (i - j = k): tối đa 1 quân hậu
    for k in range(-(n - 2), n - 1):
        diag = [x[i, i - k] for i in range(n) if 0 <= i - k < n]
        if len(diag) > 1:
            mdl.add_constraint(mdl.sum(diag) <= 1)

    # 4. Ràng buộc đường chéo phụ (i + j = k): tối đa 1 quân hậu
    for k in range(1, 2 * n - 2):
        diag = [x[i, k - i] for i in range(n) if 0 <= k - i < n]
        if len(diag) > 1:
            mdl.add_constraint(mdl.sum(diag) <= 1)

    # Thực thi giải mô hình
    sol = mdl.solve(log_output=False)
    elapsed_time = time.time() - start_time

    is_sat = sol is not None
    solution = None

    # Trích xuất ma trận nghiệm dạng bàn cờ 2D
    if is_sat:
        solution = [[int(sol.get_value(x[i, j]) > 0.5) for j in range(n)] for i in range(n)]

    return {
        "solution": solution,
        "n": n,
        "variables": n * n,
        "constraints": mdl.number_of_constraints,
        "time": elapsed_time,
        "sat": is_sat,
        "status": "OPTIMAL" if is_sat else "INFEASIBLE / TIMEOUT",
        "solver": "IBM CPLEX (MIP)"
    }


def print_solution(result):
    """Hiển thị thông tin kết quả giải và trực quan hóa bàn cờ."""
    if result is None:
        print("Không tìm thấy lời giải.")
        return

    if isinstance(result, dict):
        solution = result.get("solution")
        print(f"--- N-Queens {result.get('solver', 'IBM CPLEX (MIP)')} ---")
        print(f"Kích thước bàn cờ (N): {result.get('n')}")
        print(f"Trạng thái            : {result.get('status')} ({'SAT' if result.get('sat') else 'UNSAT'})")
        print(f"Số biến               : {result.get('variables')} (Biến nhị phân)")
        print(f"Số ràng buộc          : {result.get('constraints')} (Ràng buộc tuyến tính)")
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
    result = solve_n_queens_cplex_mip(n)
    print_solution(result)
