"""
Benchmark Suite cho các phương pháp SAT Encoding của bài toán N-Queens.

So sánh 5 phương pháp mã hóa At-Most-One (AMO):
1. Binomial (Pairwise) - O(n^2) mệnh đề, 0 biến phụ
2. Sequential Counter  - O(n) mệnh đề, O(n) biến phụ
3. Binary (Bitwise)    - O(n log n) mệnh đề, O(log n) biến phụ
4. Commander Variable  - O(n) mệnh đề, O(n/g) biến phụ (g=3)
5. 2-Product           - O(n) mệnh đề, O(sqrt(n)) biến phụ

Kết quả được lưu vào: results/data/encoding.csv
"""

import argparse
import os
import sys
import time
from pathlib import Path
import pandas as pd

# Thiết lập đường dẫn tới thư mục src
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_SRC_DIR = _PROJECT_ROOT / "src"
_DATA_DIR = _PROJECT_ROOT / "results" / "data"

if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

# Import các solver SAT và encodings từ src
from binomial import (
    solve_n_queens as solve_binomial,
    generate_variables as gen_vars_binomial,
    VarManager as VarManagerBinomial,
    generate_clauses as gen_clauses_binomial,
)
from sequential import (
    solve_n_queens as solve_sequential,
    generate_variables as gen_vars_sequential,
    VarManager as VarManagerSequential,
    generate_clauses as gen_clauses_sequential,
)
from binary import (
    solve_n_queens as solve_binary,
    generate_variables as gen_vars_binary,
    VarManager as VarManagerBinary,
    generate_clauses as gen_clauses_binary,
)
from commander import (
    solve_n_queens as solve_commander,
    generate_variables as gen_vars_commander,
    VarManager as VarManagerCommander,
    generate_clauses as gen_clauses_commander,
)
from product import (
    solve_n_queens as solve_product,
    generate_variables as gen_vars_product,
    VarManager as VarManagerProduct,
    generate_clauses as gen_clauses_product,
)
from pysat.solvers import Minisat22, Cadical153, Glucose4

# Danh sách mapping các bộ sinh mệnh đề
ENCODING_GENERATORS = {
    "binomial": (gen_vars_binomial, VarManagerBinomial, gen_clauses_binomial),
    "sequential": (gen_vars_sequential, VarManagerSequential, gen_clauses_sequential),
    "binary": (gen_vars_binary, VarManagerBinary, gen_clauses_binary),
    "commander": (gen_vars_commander, VarManagerCommander, gen_clauses_commander),
    "product": (gen_vars_product, VarManagerProduct, gen_clauses_product),
}

SOLVER_MAP = {
    "minisat22": Minisat22,
    "cadical153": Cadical153,
    "glucose4": Glucose4,
}


def benchmark_single(n, encoding_name, solver_name="glucose4", timeout=120):
    """
    Thực hiện đo đạc chi tiết cho 1 cấu hình (N, encoding, solver).
    Tách biệt thời gian sinh CNF (gen_time) và thời gian giải SAT (solve_time).
    """
    if encoding_name not in ENCODING_GENERATORS:
        raise ValueError(f"Unknown encoding: {encoding_name}")

    gen_vars_fn, var_manager_cls, gen_clauses_fn = ENCODING_GENERATORS[encoding_name]
    SolverCls = SOLVER_MAP.get(solver_name.lower(), Glucose4)

    # 1. Đo thời gian sinh mệnh đề CNF (Encoding Phase)
    t_start_gen = time.perf_counter()
    variables = gen_vars_fn(n)
    var_manager = var_manager_cls(start_id=n * n + 1)
    clauses = gen_clauses_fn(n, variables, var_manager)
    gen_time = time.perf_counter() - t_start_gen

    total_vars = var_manager.total_vars
    aux_vars = total_vars - (n * n)
    num_clauses = len(clauses)

    # 2. Đo thời gian giải SAT (Solving Phase)
    t_start_solve = time.perf_counter()
    sat = False
    status = "UNKNOWN"
    try:
        solver = SolverCls()
        for clause in clauses:
            solver.add_clause(clause)

        sat = solver.solve()
        solve_time = time.perf_counter() - t_start_solve
        status = "SAT" if sat else "UNSAT"
        solver.delete()
    except Exception as e:
        solve_time = time.perf_counter() - t_start_solve
        status = f"ERROR: {str(e)}"

    total_time = gen_time + solve_time

    return {
        "n": n,
        "encoding": encoding_name,
        "solver": solver_name,
        "variables": total_vars,
        "aux_vars": aux_vars,
        "clauses": num_clauses,
        "gen_time": round(gen_time, 6),
        "solve_time": round(solve_time, 6),
        "total_time": round(total_time, 6),
        "sat": sat,
        "status": status,
    }


def run_encoding_benchmark(
    n_list=None,
    encodings=None,
    solver_name="glucose4",
    output_csv=None,
    repeats=1,
    binomial_max_n=64,
):
    """
    Chạy toàn bộ thí nghiệm benchmark cho các phương pháp encoding.
    Lưu kết quả lũy tiến vào tệp CSV.
    """
    if n_list is None:
        n_list = [4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 48, 56, 64, 80, 96, 112, 128]
    if encodings is None:
        encodings = ["binomial", "sequential", "binary", "commander", "product"]
    if output_csv is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_csv = _DATA_DIR / "encoding.csv"
    else:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

    results = []

    print("\n" + "=" * 88)
    print(f"BENCHMARK SAT ENCODINGS FOR N-QUEENS (Solver: {solver_name})")
    print("=" * 88)
    header = (
        f"{'N':>5} | {'Encoding':<12} | {'Vars':>8} | {'AuxVars':>8} | "
        f"{'Clauses':>10} | {'GenTime(s)':>11} | {'SolveTime(s)':>12} | {'Total(s)':>10} | {'Status':<6}"
    )
    print(header)
    print("-" * len(header))

    # Xóa file cũ hoặc chuẩn bị ghi file mới
    columns = [
        "n",
        "encoding",
        "solver",
        "variables",
        "aux_vars",
        "clauses",
        "gen_time",
        "solve_time",
        "total_time",
        "sat",
        "status",
    ]
    df_init = pd.DataFrame(columns=columns)
    df_init.to_csv(output_csv, index=False)

    for n in n_list:
        for enc in encodings:
            # Binomial tạo O(n^4) mệnh đề nên cần giới hạn để tránh tràn bộ nhớ
            if enc == "binomial" and n > binomial_max_n:
                row = {
                    "n": n,
                    "encoding": enc,
                    "solver": solver_name,
                    "variables": n * n,
                    "aux_vars": 0,
                    "clauses": -1,
                    "gen_time": -1.0,
                    "solve_time": -1.0,
                    "total_time": -1.0,
                    "sat": False,
                    "status": "SKIPPED_MEMLIMIT",
                }
                results.append(row)
                pd.DataFrame([row]).to_csv(output_csv, mode="a", header=False, index=False)
                print(
                    f"{n:5d} | {enc:<12} | {'N/A':>8} | {'N/A':>8} | "
                    f"{'N/A':>10} | {'N/A':>11} | {'N/A':>12} | {'N/A':>10} | {'SKIP':<6}"
                )
                continue

            # Đo đạc qua các lần chạy (repeats)
            run_metrics = []
            for _ in range(repeats):
                m = benchmark_single(n, enc, solver_name=solver_name)
                run_metrics.append(m)

            # Tính trung bình thời gian nếu có nhiều lần chạy
            avg_res = run_metrics[0].copy()
            if repeats > 1:
                avg_res["gen_time"] = round(sum(m["gen_time"] for m in run_metrics) / repeats, 6)
                avg_res["solve_time"] = round(sum(m["solve_time"] for m in run_metrics) / repeats, 6)
                avg_res["total_time"] = round(sum(m["total_time"] for m in run_metrics) / repeats, 6)

            results.append(avg_res)

            # Ghi ngay từng dòng vào CSV
            pd.DataFrame([avg_res]).to_csv(output_csv, mode="a", header=False, index=False)

            print(
                f"{n:5d} | {enc:<12} | {avg_res['variables']:8d} | {avg_res['aux_vars']:8d} | "
                f"{avg_res['clauses']:10d} | {avg_res['gen_time']:11.5f} | {avg_res['solve_time']:12.5f} | "
                f"{avg_res['total_time']:10.5f} | {avg_res['status']:<6}"
            )

    print("=" * 88)
    print(f"[*] Benchmark hoàn tất. Kết quả được lưu tại: {output_csv}\n")
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Benchmark các phương pháp SAT Encoding cho N-Queens")
    parser.add_argument("--n_list", type=int, nargs="+", default=None, help="Danh sách giá trị N")
    parser.add_argument("--encodings", type=str, nargs="+", default=None, choices=list(ENCODING_GENERATORS.keys()), help="Danh sách encoding")
    parser.add_argument("--solver", type=str, default="glucose4", choices=list(SOLVER_MAP.keys()), help="SAT Solver backend")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file CSV xuất ra")
    parser.add_argument("--repeats", type=int, default=1, help="Số lần chạy lặp lại để lấy trung bình")
    parser.add_argument("--binomial_max_n", type=int, default=64, help="Kích thước N tối đa cho Binomial")
    args = parser.parse_args()

    run_encoding_benchmark(
        n_list=args.n_list,
        encodings=args.encodings,
        solver_name=args.solver,
        output_csv=args.output,
        repeats=args.repeats,
        binomial_max_n=args.binomial_max_n,
    )


if __name__ == "__main__":
    main()

