"""
Giải bài toán N-Queens bằng Google OR-Tools CP-SAT Solver.

Mô hình hóa Constraint Programming (CP):
- Biến quyết định: q[i] in {0, ..., n - 1} đại diện cho chỉ số cột đặt quân hậu ở hàng i.
- Ràng buộc 1 (Cột): Mỗi cột có tối đa 1 quân hậu -> AllDifferent(q)
- Ràng buộc 2 (Đường chéo chính): Không cùng đường chéo chính -> AllDifferent(q[i] - i)
- Ràng buộc 3 (Đường chéo phụ): Không cùng đường chéo phụ -> AllDifferent(q[i] + i)
"""

import time
from ortools.sat.python import cp_model


def solve_n_queens_cp_sat(n, time_limit=300, num_workers=8):
    """Giải bài toán N-Queens bằng Google OR-Tools CP-SAT Solver."""
    start_time = time.time()

    # Khởi tạo mô hình CP-SAT
    model = cp_model.CpModel()

    # N biến nguyên: q[i] là vị trí cột của quân hậu tại hàng i (0 <= q[i] < n)
    q = [model.new_int_var(0, n - 1, f"q_{i}") for i in range(n)]

    # 1. Ràng buộc cột: tất cả các cột phải khác nhau
    model.add_all_different(q)

    # 2. Ràng buộc đường chéo chính: (q[i] - i) phải khác nhau
    model.add_all_different([q[i] - i for i in range(n)])

    # 3. Ràng buộc đường chéo phụ: (q[i] + i) phải khác nhau
    model.add_all_different([q[i] + i for i in range(n)])

    # Cấu hình solver
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit

    if num_workers is not None:
        solver.parameters.num_search_workers = num_workers

    solver.parameters.log_search_progress = False

    # Thực thi giải mô hình
    status = solver.solve(model)
    elapsed_time = time.time() - start_time

    is_sat = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    solution = None

    # Trích xuất ma trận nghiệm dạng bàn cờ 2D
    if is_sat:
        solution = [[0] * n for _ in range(n)]
        for i in range(n):
            col = solver.value(q[i])
            solution[i][col] = 1

    status_str = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN / TIMEOUT"
    }.get(status, "UNKNOWN")

    return {
        "solution": solution,
        "n": n,
        "variables": n,
        "constraints": 3,
        "booleans": solver.num_booleans,
        "branches": solver.num_branches,
        "conflicts": solver.num_conflicts,
        "time": elapsed_time,
        "wall_time": solver.wall_time,
        "sat": is_sat,
        "status": status_str,
        "solver": "Google OR-Tools (CP-SAT)"
    }


def print_solution(result):
    """Hiển thị thông tin kết quả giải và trực quan hóa bàn cờ."""
    if result is None:
        print("Không tìm thấy lời giải.")
        return

    if isinstance(result, dict):
        solution = result.get("solution")
        print(f"--- N-Queens {result.get('solver', 'Google OR-Tools (CP-SAT)')} ---")
        print(f"Kích thước bàn cờ (N): {result.get('n')}")
        print(f"Trạng thái            : {result.get('status')} ({'SAT' if result.get('sat') else 'UNSAT'})")
        print(f"Số biến               : {result.get('variables')} (Biến nguyên)")
        print(f"Số ràng buộc          : {result.get('constraints')} (Ràng buộc toàn cục AllDifferent)")
        print(f"Số biến boolean nội bộ: {result.get('booleans')}")
        print(f"Số nhánh tìm kiếm     : {result.get('branches')}")
        print(f"Số xung đột           : {result.get('conflicts')}")
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
    n = 100
    result = solve_n_queens_cp_sat(n)
    print_solution(result)
