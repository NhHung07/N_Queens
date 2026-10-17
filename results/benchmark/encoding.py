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
import multiprocessing
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
    generate_variables as gen_vars_binomial,
    VarManager as VarManagerBinomial,
    generate_clauses as gen_clauses_binomial,
)
from sequential import (
    generate_variables as gen_vars_sequential,
    VarManager as VarManagerSequential,
    generate_clauses as gen_clauses_sequential,
)
from binary import (
    generate_variables as gen_vars_binary,
    VarManager as VarManagerBinary,
    generate_clauses as gen_clauses_binary,
)
from commander import (
    generate_variables as gen_vars_commander,
    VarManager as VarManagerCommander,
    generate_clauses as gen_clauses_commander,
)
from product import (
    generate_variables as gen_vars_product,
    VarManager as VarManagerProduct,
    generate_clauses as gen_clauses_product,
)
from pysat.solvers import Glucose4

# Danh sách mapping các bộ sinh mệnh đề
ENCODING_GENERATORS = {
    "binomial": (gen_vars_binomial, VarManagerBinomial, gen_clauses_binomial),
    "sequential": (gen_vars_sequential, VarManagerSequential, gen_clauses_sequential),
    "binary": (gen_vars_binary, VarManagerBinary, gen_clauses_binary),
    "commander": (gen_vars_commander, VarManagerCommander, gen_clauses_commander),
    "product": (gen_vars_product, VarManagerProduct, gen_clauses_product),
}


def _solve_clauses(clauses, result_connection):
    """Nạp CNF và giải trong tiến trình riêng để có thể dừng cứng khi timeout."""
    t_start = time.perf_counter()
    solver = Glucose4()
    try:
        for clause in clauses:
            solver.add_clause(clause)
        sat_res = solver.solve()
        result_connection.send((sat_res, time.perf_counter() - t_start))
    finally:
        solver.delete()
        result_connection.close()


def benchmark_single(n, encoding_name, timeout=100):
    """
    Thực hiện đo đạc chi tiết cho 1 cấu hình (N, encoding, solver).
    Tách biệt thời gian sinh CNF (gen_time) và thời gian giải SAT (solve_time).
    """
    if encoding_name not in ENCODING_GENERATORS:
        raise ValueError(f"Unknown encoding: {encoding_name}")

    gen_vars_fn, var_manager_cls, gen_clauses_fn = ENCODING_GENERATORS[encoding_name]
    # 1. Đo thời gian sinh mệnh đề CNF (Encoding Phase)
    t_start_gen = time.perf_counter()
    variables = gen_vars_fn(n)
    var_manager = var_manager_cls(start_id=n * n + 1)
    clauses = gen_clauses_fn(n, variables, var_manager)
    gen_time = time.perf_counter() - t_start_gen

    total_vars = var_manager.total_vars
    aux_vars = total_vars - (n * n)
    num_clauses = len(clauses)

    # 2. Nạp CNF và giải SAT trong tiến trình có giới hạn thời gian
    sat = False
    context = multiprocessing.get_context("fork")
    result_receiver, result_sender = context.Pipe(duplex=False)
    process = context.Process(target=_solve_clauses, args=(clauses, result_sender))
    process.start()
    result_sender.close()

    if result_receiver.poll(timeout):
        sat_res, solve_time = result_receiver.recv()
    else:
        sat_res, solve_time = None, timeout

    if process.is_alive():
        process.terminate()
    process.join()
    result_receiver.close()

    if sat_res is None or solve_time >= timeout:
        status = "TIMEOUT"
        solve_time = -1.0
        total_time = -1.0
    else:
        sat = bool(sat_res)
        status = "SAT" if sat else "UNSAT"
        total_time = gen_time + solve_time

    return {
        "n": n,
        "encoding": encoding_name,
        "solver": "glucose4",
        "variables": total_vars,
        "aux_vars": aux_vars,
        "clauses": num_clauses,
        "gen_time": round(gen_time, 6) if gen_time >= 0 else -1.0,
        "solve_time": round(solve_time, 6) if solve_time >= 0 else -1.0,
        "total_time": round(total_time, 6) if total_time >= 0 else -1.0,
        "sat": sat,
        "status": status,
    }


def run_encoding_benchmark(
    n_list=None,
    encodings=None,
    output_csv=None,
    repeats=1,
    binomial_max_n=343,
    timeout=100,
    force_clean=False,
):
    """
    Chạy benchmark cho các phương pháp encoding lên đến N = 1000.
    Lưu kết quả lũy tiến vào tệp CSV.
    """
    if n_list is None:
        n_list = [4, 8, 16, 25, 36, 49, 64, 81, 100, 125, 216, 343, 512, 729, 1000]
    if encodings is None:
        encodings = ["binomial", "sequential", "binary", "commander", "product"]
    if output_csv is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_csv = _DATA_DIR / "encoding.csv"
    else:
        output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Đọc dữ liệu cache hợp lệ cũ
    existing_cache = {}
    if output_csv.exists() and not force_clean:
        df_old = pd.read_csv(output_csv)
        for _, r in df_old.iterrows():
            if r["status"] == "SAT":
                existing_cache[(int(r["n"]), str(r["encoding"]))] = r.to_dict()

    results = []

    print("\n" + "=" * 88)
    print("BENCHMARK SAT ENCODINGS FOR N-QUEENS (Solver: Glucose4)")
    print("=" * 88)
    header = (
        f"{'N':>5} | {'Encoding':<12} | {'Vars':>8} | {'AuxVars':>8} | "
        f"{'Clauses':>10} | {'GenTime(s)':>11} | {'SolveTime(s)':>12} | {'Total(s)':>10} | {'Status':<6}"
    )
    print(header)
    print("-" * len(header))

    # Chuẩn bị file CSV
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
            # Kiểm tra cache
            if (n, enc) in existing_cache:
                avg_res = existing_cache[(n, enc)]
                results.append(avg_res)
                pd.DataFrame([avg_res]).to_csv(output_csv, mode="a", header=False, index=False)
                gen_s = f"{avg_res['gen_time']:11.5f}" if avg_res['gen_time'] >= 0 else "N/A"
                sol_s = f"{avg_res['solve_time']:12.5f}" if avg_res['solve_time'] >= 0 else "N/A"
                tot_s = f"{avg_res['total_time']:10.5f}" if avg_res['total_time'] >= 0 else "N/A"
                print(
                    f"{n:5d} | {enc:<12} | {int(avg_res['variables']):8d} | {int(avg_res['aux_vars']):8d} | "
                    f"{int(avg_res['clauses']):10d} | {gen_s:>11} | {sol_s:>12} | "
                    f"{tot_s:>10} | {avg_res['status']:<6}"
                )
                continue

            # Binomial tạo O(n^4) mệnh đề nên cần giới hạn để tránh tràn bộ nhớ
            if enc == "binomial" and n > binomial_max_n:
                row = {
                    "n": n,
                    "encoding": enc,
                    "solver": "glucose4",
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
                m = benchmark_single(n, enc, timeout=timeout)
                run_metrics.append(m)

            avg_res = run_metrics[0].copy()
            if repeats > 1:
                avg_res["gen_time"] = round(sum(m["gen_time"] for m in run_metrics) / repeats, 6)
                avg_res["solve_time"] = round(sum(m["solve_time"] for m in run_metrics) / repeats, 6)
                avg_res["total_time"] = round(sum(m["total_time"] for m in run_metrics) / repeats, 6)

            results.append(avg_res)
            pd.DataFrame([avg_res]).to_csv(output_csv, mode="a", header=False, index=False)

            gen_s = f"{avg_res['gen_time']:11.5f}" if avg_res['gen_time'] >= 0 else "N/A"
            sol_s = f"{avg_res['solve_time']:12.5f}" if avg_res['solve_time'] >= 0 else "N/A"
            tot_s = f"{avg_res['total_time']:10.5f}" if avg_res['total_time'] >= 0 else "N/A"
            var_s = f"{int(avg_res['variables']):8d}" if avg_res['variables'] >= 0 else "N/A"
            aux_s = f"{int(avg_res['aux_vars']):8d}" if avg_res['aux_vars'] >= 0 else "N/A"
            cls_s = f"{int(avg_res['clauses']):10d}" if avg_res['clauses'] >= 0 else "N/A"

            print(
                f"{n:5d} | {enc:<12} | {var_s:>8} | {aux_s:>8} | "
                f"{cls_s:>10} | {gen_s:>11} | {sol_s:>12} | "
                f"{tot_s:>10} | {avg_res['status']:<6}"
            )

    print("=" * 88)
    print(f"[*] Benchmark hoàn tất. Kết quả được lưu tại: {output_csv}\n")
    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Benchmark các phương pháp SAT Encoding cho N-Queens")
    parser.add_argument("--n_list", type=int, nargs="+", default=None, help="Danh sách giá trị N")
    parser.add_argument("--encodings", type=str, nargs="+", default=None, choices=list(ENCODING_GENERATORS.keys()), help="Danh sách encoding")
    parser.add_argument("--output", type=str, default=None, help="Đường dẫn file CSV xuất ra")
    parser.add_argument("--repeats", type=int, default=1, help="Số lần chạy lặp lại để lấy trung bình")
    parser.add_argument("--binomial_max_n", type=int, default=343, help="Kích thước N tối đa cho Binomial")
    parser.add_argument("--timeout", type=int, default=100, help="Giới hạn thời gian (giây) cho mỗi thí nghiệm")
    parser.add_argument("--clean", action="store_true", help="Chạy lại toàn bộ từ đầu, không dùng cache")
    args = parser.parse_args()

    run_encoding_benchmark(
        n_list=args.n_list,
        encodings=args.encodings,
        output_csv=args.output,
        repeats=args.repeats,
        binomial_max_n=args.binomial_max_n,
        timeout=args.timeout,
        force_clean=args.clean,
    )


if __name__ == "__main__":
    main()
