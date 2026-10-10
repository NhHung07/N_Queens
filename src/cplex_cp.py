"""
Giải bài toán N-Queens bằng IBM ILOG CPLEX CP Optimizer (Constraint Programming).

Mô hình hóa Constraint Programming (CP):
- Biến quyết định: q[i] in {0, ..., n - 1} đại diện cho vị trí cột đặt quân hậu ở hàng i.
- Ràng buộc 1 (Cột): Mỗi cột có tối đa 1 quân hậu -> all_diff(q)
- Ràng buộc 2 (Đường chéo chính): Không cùng đường chéo chính -> all_diff(q[i] - i)
- Ràng buộc 3 (Đường chéo phụ): Không cùng đường chéo phụ -> all_diff(q[i] + i)
"""

import time
from docplex.cp.model import CpoModel


def solve_n_queens_cplex_cp(n, time_limit=300, workers=8):
    """Giải bài toán N-Queens bằng IBM ILOG CPLEX CP Optimizer."""
    start_time = time.time()

    # Khởi tạo mô hình CPLEX CP
    mdl = CpoModel(name="N-Queens-CP")

    # N biến nguyên: q[i] là vị trí cột của quân hậu tại hàng i (0 <= q[i] < n)
    q = [mdl.integer_var(0, n - 1, name=f"q_{i}") for i in range(n)]

    # 1. Ràng buộc cột: tất cả các cột phải khác nhau
    mdl.add(mdl.all_diff(q))

    # 2. Ràng buộc đường chéo chính: (q[i] - i) phải khác nhau
    mdl.add(mdl.all_diff([q[i] - i for i in range(n)]))

    # 3. Ràng buộc đường chéo phụ: (q[i] + i) phải khác nhau
    mdl.add(mdl.all_diff([q[i] + i for i in range(n)]))

    params = {}
    if time_limit is not None:
        params["TimeLimit"] = time_limit
    if workers is not None:
        params["Workers"] = workers

    # Thực thi giải mô hình
    res = mdl.solve(log_output=False, **params)
    elapsed_time = time.time() - start_time

    is_sat = res.is_solution() if res else False
    solution = None

    # Trích xuất ma trận nghiệm dạng bàn cờ 2D
    if is_sat:
        solution = [[0] * n for _ in range(n)]
        for i in range(n):
            col = res.get_value(q[i])
            solution[i][col] = 1

    return {
        "solution": solution,
        "n": n,
        "variables": n,
        "constraints": 3,
        "time": elapsed_time,
        "sat": is_sat,
        "status": "FEASIBLE" if is_sat else "INFEASIBLE / TIMEOUT",
        "solver": "IBM CPLEX (CP Optimizer)"
    }


def print_solution(result):
    """Hiển thị thông tin kết quả giải và trực quan hóa bàn cờ."""
    if result is None:
        print("Không tìm thấy lời giải.")
        return

    if isinstance(result, dict):
        solution = result.get("solution")
        print(f"--- N-Queens {result.get('solver', 'IBM CPLEX (CP Optimizer)')} ---")
        print(f"Kích thước bàn cờ (N): {result.get('n')}")
        print(f"Trạng thái            : {result.get('status')} ({'SAT' if result.get('sat') else 'UNSAT'})")
        print(f"Số biến               : {result.get('variables')} (Biến nguyên)")
        print(f"Số ràng buộc          : {result.get('constraints')} (Ràng buộc toàn cục AllDifferent)")
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
    result = solve_n_queens_cplex_cp(n)
    print_solution(result)
