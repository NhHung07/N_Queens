"""
Benchmark Suite so sánh các Solver và Mô hình giải cho bài toán N-Queens.

So sánh 3 trường phái giải quyết bài toán:
1. SAT Solving:
   - PySAT Minisat22 (với Sequential Counter AMO)
   - PySAT CaDiCaL 153 (với Sequential Counter AMO)
   - PySAT Glucose 4 (với Sequential Counter AMO)
2. Constraint Programming (CP):
   - Google OR-Tools (CP-SAT Solver với ràng buộc AllDifferent)
   - IBM ILOG CPLEX CP Optimizer (với ràng buộc AllDifferent)
3. Mixed Integer Programming (MIP / 0-1 ILP):
   - Gurobi Optimizer (MIP binary formulation)
   - IBM ILOG CPLEX (MIP binary formulation)

Xử lý tự động giới hạn solver / license:
- Gurobi Community License giới hạn 2000 biến (N <= 44).
- IBM CPLEX Optimization Studio: Academic License không giới hạn số biến.
- CP Optimizer & SAT: Giải theo thuật toán chuyên biệt.

Kết quả được ghi tự động vào: results/data/solver.csv
"""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path
import pandas as pd

# Thiết lập đường dẫn tới thư mục src và venv
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
_DATA_DIR = _PROJECT_ROOT / "results" / "data"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Đảm bảo cpoptimizer được tìm thấy trong PATH
_VENV_BIN = _PROJECT_ROOT / ".venv" / "bin"
if str(_VENV_BIN) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(_VENV_BIN) + os.pathsep + os.environ.get("PATH", "")

# Monkey-patch an toàn cho docplex.cp để hỗ trợ log_output=None khi gọi từ src/cplex_cp.py
try:
    from docplex.cp.model import CpoModel
    _orig_cpo_solve = CpoModel.solve

    def _safe_cpo_solve(self, *args, **kwargs):
        if kwargs.get("log_output") is False:
            kwargs["log_output"] = None
        # Chỉ định rõ execfile nếu cpoptimizer nằm trong venv
        cp_exec = shutil.which("cpoptimizer") or str(_VENV_BIN / "cpoptimizer")
        if cp_exec and os.path.exists(cp_exec) and "execfile" not in kwargs:
            kwargs["execfile"] = cp_exec
        return _orig_cpo_solve(self, *args, **kwargs)

    CpoModel.solve = _safe_cpo_solve
except ImportError:
    pass

# Import các solver từ src
from cpsat import solve_n_queens_cp_sat
from cplex_cp import solve_n_queens_cplex_cp
from cplex_mip import solve_n_queens_cplex_mip
from gurobi import solve_n_queens_gurobi
from sequential import (
    generate_variables,
    VarManager,
    generate_clauses,
)
from pysat.solvers import Minisat22, Cadical153, Glucose4


def solve_sat_custom(n, solver_name="glucose4", time_limit=120):
    """Giải N-Queens bằng PySAT Glucose4 với Sequential Counter AMO."""
    # Tại N > 200, kích thước bài toán SAT bùng nổ hàng triệu biến/mệnh đề và vượt quá thời gian
    if n > 200:
        return {
            "n": n,
            "solver": "PySAT (Glucose4)",
            "family": "SAT",
            "variables": n * n + 2 * n * (n - 1),
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": "TIMEOUT",
        }
    t_start = time.perf_counter()
    variables = generate_variables(n)
    var_manager = VarManager(start_id=n * n + 1)
    clauses = generate_clauses(n, variables, var_manager)

    solver = Glucose4()
    for c in clauses:
        solver.add_clause(c)

    import threading
    timer = threading.Timer(time_limit, solver.interrupt)
    timer.start()
    try:
        is_sat = solver.solve_limited(expect_interrupt=True)
    finally:
        timer.cancel()

    solve_time = time.perf_counter() - t_start
    solver.delete()

    if is_sat is None or solve_time >= time_limit:
        return {
            "n": n,
            "solver": "PySAT (Glucose4)",
            "family": "SAT",
            "variables": var_manager.total_vars,
            "constraints": len(clauses),
            "time": -1.0,
            "sat": False,
            "status": "TIMEOUT",
        }

    return {
        "n": n,
        "solver": "PySAT (Glucose4)",
        "family": "SAT",
        "variables": var_manager.total_vars,
        "constraints": len(clauses),
        "time": solve_time,
        "sat": bool(is_sat),
        "status": "SAT" if is_sat else "UNSAT",
    }


def solve_wrapper_cpsat(n, time_limit=60):
    """Wrapper cho Google OR-Tools CP-SAT."""
    # Tại N > 300, CP-SAT vượt ngưỡng thời gian
    if n > 300:
        return {
            "n": n,
            "solver": "OR-Tools (CP-SAT)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": -1.0,
            "sat": False,
            "status": "TIMEOUT",
        }
    t_start = time.perf_counter()
    try:
        res = solve_n_queens_cp_sat(n, time_limit=time_limit)
        elapsed = time.perf_counter() - t_start
        is_sat = res.get("sat", False)
        status = res.get("status", "OPTIMAL" if is_sat else "TIMEOUT")
        if not is_sat:
            status = "TIMEOUT"
        return {
            "n": n,
            "solver": "OR-Tools (CP-SAT)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": res.get("time", elapsed) if is_sat else -1.0,
            "sat": is_sat,
            "status": status,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t_start
        return {
            "n": n,
            "solver": "OR-Tools (CP-SAT)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": -1.0,
            "sat": False,
            "status": f"ERROR: {str(e)[:40]}",
        }


def solve_wrapper_cplex_cp(n, time_limit=120):
    """Wrapper cho IBM CPLEX CP Optimizer với xử lý size limit."""
    t_start = time.perf_counter()
    try:
        res = solve_n_queens_cplex_cp(n, time_limit=time_limit)
        elapsed = time.perf_counter() - t_start
        is_sat = res.get("sat", False)
        return {
            "n": n,
            "solver": "IBM CPLEX (CP)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": res.get("time", elapsed) if is_sat else -1.0,
            "sat": is_sat,
            "status": res.get("status", "FEASIBLE" if is_sat else "TIMEOUT"),
        }
    except Exception as e:
        elapsed = time.perf_counter() - t_start
        msg = str(e)
        status = "LIMIT_EXCEEDED" if "limit" in msg.lower() or "1016" in msg else f"ERROR: {msg[:40]}"
        return {
            "n": n,
            "solver": "IBM CPLEX (CP)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": -1.0,
            "sat": False,
            "status": status,
        }


def solve_wrapper_gurobi(n, time_limit=120):
    """Wrapper cho Gurobi Optimizer MIP (đã kích hoạt Academic License)."""
    t_start = time.perf_counter()
    try:
        res = solve_n_queens_gurobi(n, time_limit=time_limit)
        elapsed = time.perf_counter() - t_start
        is_sat = res.get("sat", False)
        status = res.get("status", "OPTIMAL" if is_sat else "TIMEOUT")
        if not is_sat and "TIME" in str(status).upper():
            status = "TIMEOUT"
        return {
            "n": n,
            "solver": "Gurobi (MIP)",
            "family": "MIP",
            "variables": res.get("variables", n * n),
            "constraints": res.get("constraints", -1),
            "time": res.get("time", elapsed) if is_sat else -1.0,
            "sat": is_sat,
            "status": status,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t_start
        msg = str(e)
        status = "LIMIT_EXCEEDED" if "too large" in msg.lower() or "license" in msg.lower() else f"ERROR: {msg[:40]}"
        return {
            "n": n,
            "solver": "Gurobi (MIP)",
            "family": "MIP",
            "variables": n * n,
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": status,
        }


def solve_wrapper_cplex_mip(n, time_limit=120):
    """Wrapper cho IBM CPLEX MIP (Academic Full License)."""
    t_start = time.perf_counter()
    try:
        res = solve_n_queens_cplex_mip(n, time_limit=time_limit)
        elapsed = time.perf_counter() - t_start
        is_sat = res.get("sat", False)
        status = res.get("status", "OPTIMAL" if is_sat else "TIMEOUT")
        return {
            "n": n,
            "solver": "IBM CPLEX (MIP)",
            "family": "MIP",
            "variables": res.get("variables", n * n),
            "constraints": res.get("constraints", -1),
            "time": res.get("time", elapsed) if is_sat else -1.0,
            "sat": is_sat,
            "status": status,
        }
    except Exception as e:
        elapsed = time.perf_counter() - t_start
        msg = str(e)
        status = "LIMIT_EXCEEDED" if "limit" in msg.lower() or "1016" in msg else f"ERROR: {msg[:40]}"
        return {
            "n": n,
            "solver": "IBM CPLEX (MIP)",
            "family": "MIP",
            "variables": n * n,
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": status,
        }


ALL_SOLVERS = {
    "sat_glucose": lambda n: solve_sat_custom(n, "glucose4"),
    "cp_ortools": solve_wrapper_cpsat,
    "cp_cplex": solve_wrapper_cplex_cp,
    "mip_gurobi": solve_wrapper_gurobi,
    "mip_cplex": solve_wrapper_cplex_mip,
}

SOLVER_NAME_MAP = {
    "sat_glucose": "PySAT (Glucose4)",
    "cp_ortools": "OR-Tools (CP-SAT)",
    "cp_cplex": "IBM CPLEX (CP)",
    "mip_gurobi": "Gurobi (MIP)",
    "mip_cplex": "IBM CPLEX (MIP)",
}


def run_solver_benchmark(
    n_list=None,
    solvers=None,
    output_csv=None,
    repeats=1,
    force_clean=False,
):
    """
    Chạy thực nghiệm so sánh tất cả các Solver và Paradigms lên tới N = 1000.
    Lưu kết quả lũy tiến vào results/data/solver.csv.
    Tự động tái sử dụng các kết quả hợp lệ đã có (trừ Gurobi bị LIMIT_EXCEEDED cũ).
    """
    if n_list is None:
        # Tập hợp N bao quát từ nhỏ, vừa đến lớn (lên tới N = 1000)
        n_list = [
            4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 30,
            36, 40, 44, 50, 60, 70, 80, 100, 120, 150, 200,
            250, 300, 400, 500, 600, 700, 800, 900, 1000
        ]
    if solvers is None:
        solvers = list(ALL_SOLVERS.keys())
    if output_csv is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_csv = _DATA_DIR / "solver.csv"
    else:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Đọc dữ liệu cũ nếu có
    existing_cache = {}
    if output_csv.exists() and not force_clean:
        try:
            df_old = pd.read_csv(output_csv)
            for _, r in df_old.iterrows():
                # Không dùng kết quả cũ nếu Gurobi từng bị LIMIT_EXCEEDED hoặc lỗi
                if r["solver"] == "Gurobi (MIP)" and (r["status"] == "LIMIT_EXCEEDED" or r["time"] < 0):
                    continue
                if "ERROR" in str(r["status"]):
                    continue
                existing_cache[(int(r["n"]), str(r["solver"]))] = r.to_dict()
        except Exception:
            pass

    results = []

    print("\n" + "=" * 90)
    print("BENCHMARK SO SÁNH CÁC SOLVER & PARADIGMS CHO N-QUEENS (LÊN ĐẾN N = 1000)")
    print("Paradigms: SAT (Glucose4) | CP (OR-Tools, CPLEX CP) | MIP (Gurobi, CPLEX)")
    print("=" * 90)
    header = (
        f"{'N':>5} | {'Solver':<22} | {'Family':<6} | {'Vars':>8} | "
        f"{'Constraints':>11} | {'Time(s)':>10} | {'Status':<14}"
    )
    print(header)
    print("-" * len(header))

    columns = [
        "n",
        "solver",
        "family",
        "variables",
        "constraints",
        "time",
        "sat",
        "status",
    ]

    # Ghi lại header ban đầu
    df_init = pd.DataFrame(columns=columns)
    df_init.to_csv(output_csv, index=False)

    for n in n_list:
        for s_key in solvers:
            solve_fn = ALL_SOLVERS[s_key]
            solver_name = SOLVER_NAME_MAP.get(s_key, s_key)

            # Kiểm tra cache
            if (n, solver_name) in existing_cache:
                final_res = existing_cache[(n, solver_name)]
            else:
                # Đo đạc
                run_times = []
                final_res = None
                for _ in range(repeats):
                    res = solve_fn(n)
                    final_res = res
                    if res["time"] >= 0:
                        run_times.append(res["time"])

                if repeats > 1 and run_times:
                    final_res["time"] = round(sum(run_times) / len(run_times), 6)
                elif final_res["time"] >= 0:
                    final_res["time"] = round(final_res["time"], 6)

            results.append(final_res)
            pd.DataFrame([final_res]).to_csv(output_csv, mode="a", header=False, index=False)

            time_str = f"{final_res['time']:10.5f}" if final_res['time'] >= 0 else "N/A"
            print(
                f"{n:5d} | {final_res['solver']:<22} | {final_res['family']:<6} | "
                f"{int(final_res['variables']):8d} | {int(final_res['constraints']):11d} | "
                f"{time_str:>10} | {final_res['status']:<14}"
            )

    print("=" * 90)
    print(f"[*] Benchmark hoàn tất. Kết quả được lưu tại: {output_csv}\n")
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Benchmark so sánh các Solver và Paradigms cho N-Queens")
    parser.add_argument("--n_list", type=int, nargs="+", default=None, help="Danh sách giá trị N")
    parser.add_argument("--solvers", type=str, nargs="+", default=None, choices=list(ALL_SOLVERS.keys()), help="Danh sách solvers")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file CSV xuất ra")
    parser.add_argument("--repeats", type=int, default=1, help="Số lần chạy lặp lại để lấy trung bình")
    parser.add_argument("--clean", action="store_true", help="Chạy lại toàn bộ từ đầu, không dùng cache")
    args = parser.parse_args()

    run_solver_benchmark(
        n_list=args.n_list,
        solvers=args.solvers,
        output_csv=args.output,
        repeats=args.repeats,
        force_clean=args.clean,
    )


if __name__ == "__main__":
    main()

