"""
Giải bài toán N-Queens bằng Gurobi Optimizer (MIP / 0-1 Integer Programming).

Mô hình hóa Mixed Integer Programming (MIP):
- Biến quyết định: x[i, j] in {0, 1} = 1 nếu đặt quân hậu tại ô (i, j).
- Ràng buộc 1 (Hàng): Mỗi hàng có đúng 1 quân hậu -> sum_j x[i, j] == 1
- Ràng buộc 2 (Cột): Mỗi cột có đúng 1 quân hậu -> sum_i x[i, j] == 1
- Ràng buộc 3 (Đường chéo chính): Mỗi đường chéo chính có tối đa 1 quân hậu -> sum x <= 1
- Ràng buộc 4 (Đường chéo phụ): Mỗi đường chéo phụ có tối đa 1 quân hậu -> sum x <= 1
"""

import time

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:
    gp = None
    GRB = None


def solve_n_queens_gurobi(n, time_limit=300, threads=8):
    """Giải bài toán N-Queens bằng Gurobi Optimizer (MIP)."""
    if gp is None:
        raise ImportError("Thư viện 'gurobipy' chưa được cài đặt. Vui lòng cài đặt: pip install gurobipy")

    start_time = time.time()

    # Khởi tạo mô hình Gurobi
    model = gp.Model("N-Queens")
    model.setParam("OutputFlag", 0)  # Tắt log dòng lệnh

    if time_limit is not None:
        model.setParam("TimeLimit", time_limit)
    if threads is not None:
        model.setParam("Threads", threads)

    # N^2 biến nhị phân x[i, j] in {0, 1}
    x = model.addVars(n, n, vtype=GRB.BINARY, name="x")

    # 1. Ràng buộc hàng: mỗi hàng có đúng 1 quân hậu
    for i in range(n):
        model.addConstr(gp.quicksum(x[i, j] for j in range(n)) == 1, name=f"row_{i}")

    # 2. Ràng buộc cột: mỗi cột có đúng 1 quân hậu
    for j in range(n):
        model.addConstr(gp.quicksum(x[i, j] for i in range(n)) == 1, name=f"col_{j}")

    # 3. Ràng buộc đường chéo chính (i - j = k): tối đa 1 quân hậu
    for k in range(-(n - 2), n - 1):
        diag = [x[i, i - k] for i in range(n) if 0 <= i - k < n]
        if len(diag) > 1:
            model.addConstr(gp.quicksum(diag) <= 1)

    # 4. Ràng buộc đường chéo phụ (i + j = k): tối đa 1 quân hậu
    for k in range(1, 2 * n - 2):
        diag = [x[i, k - i] for i in range(n) if 0 <= k - i < n]
        if len(diag) > 1:
            model.addConstr(gp.quicksum(diag) <= 1)

    # Thực thi tối ưu hóa
    model.optimize()
    elapsed_time = time.time() - start_time

    is_sat = model.status in (GRB.OPTIMAL, GRB.SUBOPTIMAL)
    solution = None

    # Trích xuất ma trận nghiệm dạng bàn cờ 2D
    if is_sat:
        solution = [[int(x[i, j].X > 0.5) for j in range(n)] for i in range(n)]

    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.TIME_LIMIT: "TIMEOUT",
    }.get(model.status, "UNKNOWN")

    return {
        "solution": solution,
        "n": n,
        "variables": n * n,
        "constraints": model.NumConstrs,
        "time": elapsed_time,
        "sat": is_sat,
        "status": status_str,
        "solver": "Gurobi (MIP)"
    }


def print_solution(result):
    """Hiển thị thông tin kết quả giải và trực quan hóa bàn cờ."""
    if result is None:
        print("Không tìm thấy lời giải.")
        return

    if isinstance(result, dict):
        solution = result.get("solution")
        print(f"--- N-Queens {result.get('solver', 'Gurobi (MIP)')} ---")
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
    try:
        result = solve_n_queens_gurobi(n)
        print_solution(result)
    except ImportError as e:
        print(f"[*] {e}")
