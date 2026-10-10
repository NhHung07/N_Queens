"""
Bộ điều phối và đánh giá thực nghiệm (Benchmark) cho các SAT Encodings của bài toán N-Queens.

Tổng hợp 5 phương pháp mã hóa At-Most-One (AMO):
1. Binomial (Pairwise)    - src/binomial.py
2. Sequential Counter     - src/sequential.py
3. Binary (Bitwise)       - src/binary.py
4. Commander Variable     - src/commander.py
5. 2-Product              - src/product.py
"""

import argparse
import sys
import time
from pathlib import Path

# Đảm bảo import được các module encoding dù chạy từ bất kỳ đâu
_SRC_DIR = Path(__file__).resolve().parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from binomial import solve_n_queens as solve_binomial, print_solution as print_binomial
from sequential import solve_n_queens as solve_sequential, print_solution as print_sequential
from binary import solve_n_queens as solve_binary, print_solution as print_binary
from commander import solve_n_queens as solve_commander, print_solution as print_commander
from product import solve_n_queens as solve_product, print_solution as print_product

# Bảng tra cứu ánh xạ tên encoding tới hàm giải và hàm in tương ứng
SOLVERS = {
    "binomial": (solve_binomial, print_binomial),
    "pairwise": (solve_binomial, print_binomial),
    "sequential": (solve_sequential, print_sequential),
    "seqcounter": (solve_sequential, print_sequential),
    "binary": (solve_binary, print_binary),
    "bitwise": (solve_binary, print_binary),
    "commander": (solve_commander, print_commander),
    "product": (solve_product, print_product),
}


def benchmark(n_list, encodings=None):
    """Thực hiện thí nghiệm so sánh hiệu năng giữa các phương pháp encoding."""
    if encodings is None:
        encodings = ["binomial", "sequential", "binary", "commander", "product"]

    print("\n" + "=" * 65)
    print("BENCHMARK SO SÁNH CÁC PHƯƠNG PHÁP SAT ENCODING CHO N-QUEENS")
    print("=" * 65)
    header = f"{'N':>5} | {'Encoding':<12} | {'Vars':>8} | {'Clauses':>10} | {'Time(s)':>10} | {'Status':<7}"
    print(header)
    print("-" * len(header))

    for n in n_list:
        for enc in encodings:
            solve_fn, _ = SOLVERS[enc]
            res = solve_fn(n)
            status = "SAT" if res["sat"] else "UNSAT"
            print(f"{n:5d} | {enc:<12} | {res['variables']:8d} | {res['clauses']:10d} | {res['time']:10.4f} | {status:<7}")
    print("=" * 65)


def main():
    """Giao diện dòng lệnh (CLI) điều khiển việc giải bài toán hoặc chạy benchmark."""
    parser = argparse.ArgumentParser(description="Bộ điều phối và đánh giá N-Queens SAT Solvers")
    parser.add_argument("-n", "--n", type=int, default=8, help="Kích thước bàn cờ N x N")
    parser.add_argument("-e", "--encoding", type=str, default="binary", choices=list(SOLVERS.keys()), help="Phương pháp mã hóa AMO")
    parser.add_argument("--benchmark", action="store_true", help="Chạy benchmark so sánh các phương pháp encoding")
    parser.add_argument("--n_list", type=int, nargs="+", default=[8, 16, 32, 64], help="Danh sách N để chạy benchmark")
    args = parser.parse_args()

    if args.benchmark:
        benchmark(args.n_list)
        return

    solve_fn, print_fn = SOLVERS[args.encoding]
    result = solve_fn(args.n)
    print_fn(result)


if __name__ == "__main__":
    main()
