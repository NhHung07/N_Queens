"""
Benchmark Suite so sánh các Solver và Mô hình giải cho bài toán N-Queens.

So sánh 3 trường phái giải quyết bài toán:
1. SAT Solving:
   - PySAT Glucose 4 (với Commander Variable AMO)
2. Constraint Programming (CP):
   - Google OR-Tools (CP-SAT Solver với ràng buộc AllDifferent)
   - IBM ILOG CPLEX CP Optimizer (với ràng buộc AllDifferent)
3. Mixed Integer Programming (MIP / 0-1 ILP):
   - Gurobi Optimizer (MIP binary formulation)
   - IBM ILOG CPLEX (MIP binary formulation)

Tất cả các Solver được chạy với bản quyền đầy đủ không giới hạn số biến.
Tập giá trị N thử nghiệm đồng bộ hoàn toàn với benchmark/encoding.py:
N in [4, 8, 16, 25, 36, 49, 64, 81, 100, 125, 216, 343, 512, 729, 1000]

Kết quả được ghi tự động vào: results/data/solver.csv
"""

import argparse
import os
import shutil
import sys
import threading
import time
from pathlib import Path
import pandas as pd

# Thiết lập đường dẫn tới thư mục src và venv
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
_DATA_DIR = _PROJECT_ROOT / "results" / "data"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Đảm bảo cpoptimizer được tìm thấy trong PATH nếu có trong .venv
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
from commander import (
    generate_variables,
    VarManager,
    generate_clauses,
)
from pysat.solvers import Glucose4


def solve_sat_custom(n, time_limit=120):
    """Giải N-Queens bằng PySAT Glucose4 với Commander Variable AMO."""
    t_start = time.perf_counter()
    try:
        variables = generate_variables(n)
        var_manager = VarManager(start_id=n * n + 1)
        clauses = generate_clauses(n, variables, var_manager)

        solver = Glucose4()
        for c in clauses:
            solver.add_clause(c)

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
    except Exception as e:
        return {
            "n": n,
            "solver": "PySAT (Glucose4)",
            "family": "SAT",
            "variables": n * n,
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": f"ERROR: {str(e)[:40]}",
        }


def solve_wrapper_cpsat(n, time_limit=120):
    """Wrapper cho Google OR-Tools CP-SAT."""
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
    """Wrapper cho IBM CPLEX CP Optimizer."""
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
        return {
            "n": n,
            "solver": "IBM CPLEX (CP)",
            "family": "CP",
            "variables": n,
            "constraints": 3,
            "time": -1.0,
            "sat": False,
            "status": f"ERROR: {str(e)[:40]}",
        }


def solve_wrapper_gurobi(n, time_limit=120):
    """Wrapper cho Gurobi Optimizer MIP."""
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
        return {
            "n": n,
            "solver": "Gurobi (MIP)",
            "family": "MIP",
            "variables": n * n,
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": f"ERROR: {str(e)[:40]}",
        }


def solve_wrapper_cplex_mip(n, time_limit=120):
    """Wrapper cho IBM CPLEX MIP."""
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
        return {
            "n": n,
            "solver": "IBM CPLEX (MIP)",
            "family": "MIP",
            "variables": n * n,
            "constraints": -1,
            "time": -1.0,
            "sat": False,
            "status": f"ERROR: {str(e)[:40]}",
        }


# Cấu hình danh mục solver
SOLVERS_CONFIG = {
    "sat_glucose": {
        "name": "PySAT (Glucose4)",
        "family": "SAT",
        "func": solve_sat_custom,
    },
    "cp_ortools": {
        "name": "OR-Tools (CP-SAT)",
        "family": "CP",
        "func": solve_wrapper_cpsat,
    },
    "cp_cplex": {
        "name": "IBM CPLEX (CP)",
        "family": "CP",
        "func": solve_wrapper_cplex_cp,
    },
    "mip_gurobi": {
        "name": "Gurobi (MIP)",
        "family": "MIP",
        "func": solve_wrapper_gurobi,
    },
    "mip_cplex": {
        "name": "IBM CPLEX (MIP)",
        "family": "MIP",
        "func": solve_wrapper_cplex_mip,
    },
}

ALL_SOLVERS = {k: v["func"] for k, v in SOLVERS_CONFIG.items()}
SOLVER_NAME_MAP = {k: v["name"] for k, v in SOLVERS_CONFIG.items()}


def benchmark_single(n, solver_key, timeout=120):
    """
    Thực hiện đo đạc cho 1 cấu hình (N, solver) với ngưỡng timeout xác định.
    Tương đồng với benchmark_single trong benchmark/encoding.py.
    """
    if solver_key not in SOLVERS_CONFIG:
        raise ValueError(f"Unknown solver: {solver_key}")

    cfg = SOLVERS_CONFIG[solver_key]
    solve_fn = cfg["func"]

    res = solve_fn(n, time_limit=timeout)
    if res["time"] >= 0:
        res["time"] = round(res["time"], 6)

    return res


def run_solver_benchmark(
    n_list=None,
    solvers=None,
    output_csv=None,
    repeats=1,
    timeout=120,
    force_clean=False,
):
    """
    Chạy thực nghiệm so sánh tất cả các Solver và Paradigms lên tới N = 1000.
    Danh sách N mặc định đồng bộ hoàn toàn với benchmark/encoding.py.
    Lưu kết quả lũy tiến vào results/data/solver.csv, tự động cập nhật hoặc gộp dữ liệu.
    """
    if n_list is None:
        # Đồng bộ hoàn toàn với danh sách N trong results/benchmark/encoding.py
        n_list = [4, 8, 16, 25, 36, 49, 64, 81, 100, 125, 216, 343, 512, 729, 1000]
    if solvers is None:
        solvers = list(SOLVERS_CONFIG.keys())
    if output_csv is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_csv = _DATA_DIR / "solver.csv"
    else:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

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

    solver_order = {s["name"]: i for i, s in enumerate(SOLVERS_CONFIG.values())}

    # Đọc dữ liệu cũ nếu có để hỗ trợ cập nhật lũy tiến và bảo toàn các kết quả khác
    all_records = {}
    existing_cache = {}
    if output_csv.exists() and not force_clean:
        try:
            df_old = pd.read_csv(output_csv)
            for _, r in df_old.iterrows():
                rec = r.to_dict()
                key = (int(rec["n"]), str(rec["solver"]))
                all_records[key] = rec
                # Chỉ cache các kết quả thành công hợp lệ
                if rec.get("sat") is True or rec.get("status") in ("OPTIMAL", "FEASIBLE", "SAT"):
                    existing_cache[key] = rec
        except Exception:
            pass

    def _flush_csv():
        if all_records:
            sorted_records = sorted(
                all_records.values(),
                key=lambda r: (int(r["n"]), solver_order.get(r.get("solver", ""), 99))
            )
            pd.DataFrame(sorted_records)[columns].to_csv(output_csv, index=False)

    if force_clean or not output_csv.exists():
        df_init = pd.DataFrame(columns=columns)
        df_init.to_csv(output_csv, index=False)

    results = []

    print("\n" + "=" * 90)
    print("BENCHMARK SO SÁNH CÁC SOLVER & PARADIGMS CHO N-QUEENS (LÊN ĐẾN N = 1000)")
    print("Paradigms: SAT (Glucose4) | CP (OR-Tools, CPLEX CP) | MIP (Gurobi, CPLEX)")
    print(f"Giới hạn thời gian (Timeout): {timeout}s | Chế độ: {'Ghi đè (--clean)' if force_clean else 'Cập nhật lũy tiến'}")
    print("=" * 90)
    header = (
        f"{'N':>5} | {'Solver':<20} | {'Family':<6} | {'Vars':>8} | "
        f"{'Constraints':>11} | {'Time(s)':>10} | {'Status':<14}"
    )
    print(header)
    print("-" * len(header))

    for n in n_list:
        for s_key in solvers:
            solver_name = SOLVERS_CONFIG[s_key]["name"]

            # 1. Kiểm tra cache
            if (n, solver_name) in existing_cache:
                avg_res = existing_cache[(n, solver_name)]
                results.append(avg_res)
                all_records[(n, solver_name)] = avg_res
                _flush_csv()

                time_val = avg_res.get("time", -1.0)
                var_val = avg_res.get("variables", -1)
                ct_val = avg_res.get("constraints", -1)

                try:
                    time_s = f"{float(time_val):10.5f}" if float(time_val) >= 0 else "N/A"
                except (ValueError, TypeError):
                    time_s = "N/A"

                try:
                    var_s = f"{int(float(var_val)):8d}" if float(var_val) >= 0 else "N/A"
                except (ValueError, TypeError):
                    var_s = "N/A"

                try:
                    ct_s = f"{int(float(ct_val)):11d}" if float(ct_val) >= 0 else "N/A"
                except (ValueError, TypeError):
                    ct_s = "N/A"

                print(
                    f"{n:5d} | {avg_res['solver']:<20} | {avg_res['family']:<6} | "
                    f"{var_s:>8} | {ct_s:>11} | "
                    f"{time_s:>10} | {avg_res['status']:<14}"
                )
                continue

            # 2. Đo đạc qua các lần chạy (repeats)
            run_metrics = []
            for _ in range(repeats):
                m = benchmark_single(n, s_key, timeout=timeout)
                run_metrics.append(m)

            avg_res = run_metrics[0].copy()
            if repeats > 1:
                valid_times = [m["time"] for m in run_metrics if m["time"] >= 0]
                if valid_times:
                    avg_res["time"] = round(sum(valid_times) / len(valid_times), 6)

            results.append(avg_res)
            all_records[(n, solver_name)] = avg_res
            _flush_csv()

            time_val = avg_res.get("time", -1.0)
            var_val = avg_res.get("variables", -1)
            ct_val = avg_res.get("constraints", -1)

            try:
                time_s = f"{float(time_val):10.5f}" if float(time_val) >= 0 else "N/A"
            except (ValueError, TypeError):
                time_s = "N/A"

            try:
                var_s = f"{int(float(var_val)):8d}" if float(var_val) >= 0 else "N/A"
            except (ValueError, TypeError):
                var_s = "N/A"

            try:
                ct_s = f"{int(float(ct_val)):11d}" if float(ct_val) >= 0 else "N/A"
            except (ValueError, TypeError):
                ct_s = "N/A"

            print(
                f"{n:5d} | {avg_res['solver']:<20} | {avg_res['family']:<6} | "
                f"{var_s:>8} | {ct_s:>11} | "
                f"{time_s:>10} | {avg_res['status']:<14}"
            )

    print("=" * 90)
    print(f"[*] Benchmark hoàn tất. Kết quả được lưu tại: {output_csv}\n")
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Benchmark so sánh các Solver và Paradigms cho N-Queens")
    parser.add_argument("--n_list", type=int, nargs="+", default=None, help="Danh sách giá trị N")
    parser.add_argument("--solvers", type=str, nargs="+", default=None, choices=list(SOLVERS_CONFIG.keys()), help="Danh sách solvers")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file CSV xuất ra")
    parser.add_argument("--repeats", type=int, default=1, help="Số lần chạy lặp lại để lấy trung bình")
    parser.add_argument("--timeout", type=int, default=120, help="Giới hạn thời gian (giây) cho mỗi thí nghiệm (mặc định: 120)")
    parser.add_argument("--clean", action="store_true", help="Chạy lại toàn bộ từ đầu, không dùng cache")
    args = parser.parse_args()

    run_solver_benchmark(
        n_list=args.n_list,
        solvers=args.solvers,
        output_csv=args.output,
        repeats=args.repeats,
        timeout=args.timeout,
        force_clean=args.clean,
    )


if __name__ == "__main__":
    main()
