"""
Closest Pair of Points -- Brute Force vs Divide and Conquer
===========================================================
Usage:
    python closest_pair.py                 # prompts for N on standard input
    echo 100 | python closest_pair.py      # N from a pipe
    python closest_pair.py --n 100 --seed 7
    python closest_pair.py --n 100 --int   # integer coordinates
    python closest_pair.py --n 40 --no-animate   # skip animation

Output (first three lines):
    Brute-Force: <dist, 6 dp> (x1, y1) (x2, y2)
    Divide-and-Conquer: <dist, 6 dp> (x1, y1) (x2, y2)
    Execution time: Brute-Force = <ms> ms, Divide-and-Conquer = <ms> ms

Files written: closest_pair.png (point field), performance.png (time vs N),
recursion.gif (animation of recursive split/merge).

Requirements:
    pip install matplotlib
"""

import argparse
import heapq
import math
import random
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

Point = Tuple[float, float]


@dataclass
class PairResult:
    distance: float
    p1: Optional[Point]
    p2: Optional[Point]


NO_PAIR = PairResult(float("inf"), None, None)


# --------------------------------------------------------------------------
# Core helpers
# --------------------------------------------------------------------------
def distance(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def pair_key(a: Point, b: Point):
    """Canonical (sorted) pair; gives deterministic tie-breaking."""
    return (a, b) if a <= b else (b, a)


def y_key(p: Point):
    return (p[1], p[0])


# --------------------------------------------------------------------------
# Algorithm 1: Brute force, O(N^2)
# --------------------------------------------------------------------------
def brute_force(points: List[Point]) -> PairResult:
    n = len(points)
    if n < 2:
        return NO_PAIR

    best_d = float("inf")
    best_pair = None
    for i in range(n - 1):
        pi = points[i]
        for j in range(i + 1, n):
            d = distance(pi, points[j])
            if d <= best_d:  # only build the key when it can matter
                cand = pair_key(pi, points[j])
                if best_pair is None or d < best_d or cand < best_pair:
                    best_d, best_pair = d, cand
    return PairResult(best_d, best_pair[0], best_pair[1])


# --------------------------------------------------------------------------
# Algorithm 2: Divide and conquer, O(N log N)
# --------------------------------------------------------------------------
def _better(a: PairResult, b: PairResult) -> PairResult:
    if a.distance != b.distance:
        return a if a.distance < b.distance else b
    if a.p1 is None:
        return b
    if b.p1 is None:
        return a
    return a if pair_key(a.p1, a.p2) <= pair_key(b.p1, b.p2) else b


def closest_pair_divide_conquer(points: List[Point], trace=None) -> PairResult:
    """
    Points are sorted by x once. Each recursive call returns its best pair and
    its points sorted by y (merged in linear time), so the total cost is
    O(N log N). Duplicate points need no special handling: the split is by
    index, never by value, and the strip scan compares with d = 0 correctly.

    If `trace` is a list, events describing every split/base/merge step are
    appended to it (used only for visualisation).
    """
    if len(points) < 2:
        return NO_PAIR

    px = sorted(points, key=lambda p: (p[0], p[1]))

    def solve(xs: List[Point], depth: int):
        size = len(xs)
        if trace is not None:
            trace.append({"kind": "split", "points": list(xs), "depth": depth})

        if size <= 3:
            result = brute_force(xs)
            if trace is not None:
                trace.append({"kind": "base", "points": list(xs),
                              "depth": depth, "result": result})
            return result, sorted(xs, key=y_key)

        mid = size // 2
        mid_x = (xs[mid - 1][0] + xs[mid][0]) / 2.0
        left_res, left_y = solve(xs[:mid], depth + 1)
        right_res, right_y = solve(xs[mid:], depth + 1)
        ys = list(heapq.merge(left_y, right_y, key=y_key))

        best = _better(left_res, right_res)
        d = best.distance
        strip = [p for p in ys if abs(p[0] - mid_x) <= d]
        if trace is not None:
            trace.append({"kind": "merge", "points": list(xs), "depth": depth,
                          "mid_x": mid_x, "d": d, "strip": list(strip),
                          "result": best})

        # Only points within d in y need checking (at most ~7 per point).
        for i in range(len(strip)):
            p = strip[i]
            j = i + 1
            while j < len(strip) and strip[j][1] - p[1] <= best.distance:
                q = strip[j]
                cd = distance(p, q)
                if cd <= best.distance:
                    cand = pair_key(p, q)
                    if cd < best.distance or cand < pair_key(best.p1, best.p2):
                        best = PairResult(cd, cand[0], cand[1])
                j += 1

        if trace is not None:
            trace.append({"kind": "merged", "points": list(xs), "depth": depth,
                          "mid_x": mid_x, "d": best.distance,
                          "strip": list(strip), "result": best})
        return best, ys

    return solve(px, 0)[0]


# --------------------------------------------------------------------------
# Input generation, formatting, timing
# --------------------------------------------------------------------------
def random_points(n: int, seed: Optional[int] = None, integer: bool = False,
                  span: int = 100) -> List[Point]:
    """Random points; integer or 3-decimal floating-point coordinates.
    Duplicates are possible (and handled)."""
    rng = random.Random(seed)
    if integer:
        return [(rng.randint(0, span), rng.randint(0, span)) for _ in range(n)]
    return [(round(rng.uniform(0, span), 3), round(rng.uniform(0, span), 3))
            for _ in range(n)]


def fmt_coord(v) -> str:
    return str(v) if isinstance(v, int) else f"{v:.3f}"


def fmt_point(p: Point) -> str:
    return f"({fmt_coord(p[0])}, {fmt_coord(p[1])})"


def format_result(label: str, r: PairResult) -> str:
    if r.p1 is None:
        return f"{label}: undefined (fewer than 2 points, no pair exists)"
    return f"{label}: {r.distance:.6f} {fmt_point(r.p1)} {fmt_point(r.p2)}"


def time_algorithm(func, points, repeats=1):
    """Return (result, best time in ms over `repeats` runs)."""
    best, result = float("inf"), None
    for _ in range(repeats):
        t0 = time.perf_counter()
        result = func(points)
        best = min(best, (time.perf_counter() - t0) * 1000)
    return result, best


def distances_agree(a: PairResult, b: PairResult) -> bool:
    if a.p1 is None or b.p1 is None:
        return a.p1 is None and b.p1 is None
    return math.isclose(a.distance, b.distance, rel_tol=1e-12, abs_tol=1e-12)


# --------------------------------------------------------------------------
# Verification: corner cases + randomized stress test
# --------------------------------------------------------------------------
def run_self_tests(trials: int = 300, seed: int = 2024) -> int:
    """Raises AssertionError on any disagreement; returns number of cases."""
    cases = [
        [],                                              # N = 0
        [(1, 1)],                                        # N = 1
        [(0, 0), (3, 4)],                                # N = 2
        [(2, 2), (2, 2)],                                # N = 2 identical
        [(1, 1), (5, 5), (1, 1), (9, 9), (7, 2)],        # duplicates
        [(i, 0) for i in range(0, 50, 3)],               # collinear, same y
        [(4, i * i) for i in range(12)],                 # collinear, same x
        [(i, i) for i in range(20)],                     # collinear diagonal
        [(3, 3)] * 10,                                   # all identical
        [(x, y) for x in range(8) for y in range(8)],    # grid: many ties
        [(0, 0), (1e9, 1e9), (1e9 + 1, 1e9), (-5, -5)],  # large / negative
    ]
    rng = random.Random(seed)
    for _ in range(trials):
        n = rng.choice([2, 3, 4, 5, 7, 10, 20, 50, 120])
        mode = rng.choice(["float", "int_small", "int_wide", "same_x", "same_y"])
        if mode == "float":
            pts = [(rng.uniform(-100, 100), rng.uniform(-100, 100)) for _ in range(n)]
        elif mode == "int_small":  # lots of duplicates
            pts = [(rng.randint(0, 6), rng.randint(0, 6)) for _ in range(n)]
        elif mode == "int_wide":
            pts = [(rng.randint(-500, 500), rng.randint(-500, 500)) for _ in range(n)]
        elif mode == "same_x":
            pts = [(7, rng.randint(0, 1000)) for _ in range(n)]
        else:
            pts = [(rng.randint(0, 1000), -3) for _ in range(n)]
        cases.append(pts)

    for pts in cases:
        b, d = brute_force(pts), closest_pair_divide_conquer(pts)
        assert distances_agree(b, d), f"Mismatch on {pts[:6]}...: {b} vs {d}"
        if b.p1 is not None:
            # The reported pair must really be two input points at that distance.
            for r in (b, d):
                assert r.p1 in pts and r.p2 in pts
                assert math.isclose(distance(r.p1, r.p2), r.distance,
                                    rel_tol=1e-12, abs_tol=1e-12)
    return len(cases)


# --------------------------------------------------------------------------
# Visual style
# --------------------------------------------------------------------------
BG, PANEL, GRID = "#071426", "#0B1D33", "#183957"
TEXT, MUTED = "#E7F0FF", "#9BB4D1"
CYAN, PINK, AMBER, MINT, VIOLET = "#36D7FF", "#FF4D88", "#FFC247", "#45E0B8", "#C078FF"


def style_axis(ax, title=None):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.label.set_color(TEXT)
    ax.yaxis.label.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.grid(True, color=GRID, linewidth=0.7, alpha=0.75)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=TEXT, fontsize=12, fontweight="bold",
                     pad=12, loc="left")


# --------------------------------------------------------------------------
# Performance analysis (running time vs N)
# --------------------------------------------------------------------------
def performance_analysis(seed: int = 1234, integer: bool = False):
    sizes = [10, 25, 50, 100, 200, 400, 800, 1200, 1600, 2400]
    brute_times, dc_times = [], []
    rng = random.Random(seed)
    print("\nPERFORMANCE ANALYSIS")
    print(f"{'N':>7} {'Brute Force (ms)':>18} {'Divide & Conquer (ms)':>23} {'Agree':>7}")
    for n in sizes:
        if integer:
            pts = [(rng.randint(0, 10 * n), rng.randint(0, 10 * n)) for _ in range(n)]
        else:
            pts = [(round(rng.random() * 1000, 5), round(rng.random() * 1000, 5))
                   for _ in range(n)]
        repeats = 5 if n <= 200 else 2
        b, bt = time_algorithm(brute_force, pts, repeats)
        d, dt = time_algorithm(closest_pair_divide_conquer, pts, repeats)
        agree = distances_agree(b, d)
        print(f"{n:7d} {bt:18.4f} {dt:23.4f} {str(agree):>7}")
        if not agree:
            raise AssertionError(f"Algorithms disagree at N={n}: {b} vs {d}")
        brute_times.append(bt)
        dc_times.append(dt)

    fig, ax = plt.subplots(figsize=(10.5, 6.0), facecolor=BG)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.84, bottom=0.16)
    style_axis(ax, "RUNTIME PROFILE  /  INPUT SIZE vs EXECUTION TIME")
    ax.plot(sizes, brute_times, color=PINK, marker="o", markersize=6, linewidth=2.5,
            label="Brute Force (measured)", markeredgecolor=BG, markeredgewidth=1.2)
    ax.plot(sizes, dc_times, color=AMBER, marker="D", markersize=5.5, linewidth=2.5,
            label="Divide & Conquer (measured)", markeredgecolor=BG, markeredgewidth=1.2)
    # Theoretical reference curves, scaled to pass through the last measurement.
    n_last = sizes[-1]
    ax.plot(sizes, [brute_times[-1] * (n / n_last) ** 2 for n in sizes],
            color=PINK, linestyle=":", linewidth=1.4, alpha=0.8, label="O(N²) reference")
    ref = n_last * math.log2(n_last)
    ax.plot(sizes, [dc_times[-1] * (n * math.log2(n)) / ref for n in sizes],
            color=AMBER, linestyle=":", linewidth=1.4, alpha=0.8,
            label="O(N log N) reference")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Number of points (N)", labelpad=10)
    ax.set_ylabel("Execution time (milliseconds)", labelpad=10)
    ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT, framealpha=1,
              loc="upper left")
    fig.suptitle("CLOSEST PAIR  /  PERFORMANCE BENCHMARK", color=TEXT, fontsize=16,
                 fontweight="bold", x=0.06, ha="left", y=0.96)
    fig.text(0.06, 0.905, "Same point sets for both algorithms · logarithmic axes",
             color=MUTED, fontsize=9)
    fig.savefig("performance.png", dpi=180, facecolor=fig.get_facecolor())
    print("Saved running-time graph as performance.png")
    return sizes, brute_times, dc_times


# --------------------------------------------------------------------------
# Point-field plot
# --------------------------------------------------------------------------
def plot_points(points: List[Point], brute: PairResult, dc: PairResult, trace=None):
    fig, ax = plt.subplots(figsize=(10.5, 8), facecolor=BG)
    fig.subplots_adjust(left=0.10, right=0.97, top=0.85, bottom=0.12)
    style_axis(ax)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    ax.scatter(xs, ys, c=CYAN, s=31, alpha=0.88, edgecolors="#D8F8FF",
               linewidths=0.35, label=f"Input points · N={len(points)}", zorder=3)

    # Top-level divide line + strip (the root merge is the only depth-0 merge).
    root = next((e for e in (trace or []) if e["kind"] == "merge" and e["depth"] == 0),
                None)
    if root is not None:
        mid_x, d = root["mid_x"], root["d"]
        ymin, ymax = min(ys), max(ys)
        ax.axvline(mid_x, color=MINT, linestyle=(0, (5, 4)), linewidth=1.8,
                   label="Divide line (top level)", zorder=2)
        ax.add_patch(Rectangle((mid_x - d, ymin), 2 * d, max(ymax - ymin, 1e-9),
                               facecolor=VIOLET, alpha=0.16, edgecolor=VIOLET,
                               linestyle="--", linewidth=1.4,
                               label=f"Strip region · width 2d (d={d:.4f})", zorder=1))
        if root["strip"]:
            ax.scatter([p[0] for p in root["strip"]], [p[1] for p in root["strip"]],
                       facecolors="none", edgecolors=VIOLET, s=85, linewidths=1.2,
                       label="Points inside strip", zorder=4)

    # Brute force drawn solid, D&C dashed on top: identical pairs stay visible.
    specs = ((brute, PINK, "-", "Brute Force pair", 10),
             (dc, AMBER, (0, (3, 2)), "Divide & Conquer pair", -17))
    for r, color, ls, label, off in specs:
        if r.p1 is None:
            continue
        ax.plot([r.p1[0], r.p2[0]], [r.p1[1], r.p2[1]], color=color, linestyle=ls,
                linewidth=3, marker="o", markersize=7, markeredgecolor=BG,
                markeredgewidth=1.1, label=f"{label} · d={r.distance:.6f}", zorder=7)
        ax.annotate(f"{r.distance:.3f}",
                    ((r.p1[0] + r.p2[0]) / 2, (r.p1[1] + r.p2[1]) / 2),
                    xytext=(8, off), textcoords="offset points", color=color,
                    fontsize=9, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.25", facecolor=BG,
                              edgecolor=color, alpha=0.95))

    # Zoomed inset: the closest pair is often smaller than a pixel at full scale.
    ref = dc if dc.p1 is not None else brute
    if ref.p1 is not None:
        cx = (ref.p1[0] + ref.p2[0]) / 2
        cy = (ref.p1[1] + ref.p2[1]) / 2
        half = ref.distance * 2 if ref.distance > 0 else 0.5
        inset = ax.inset_axes([0.68, 0.06, 0.28, 0.28])
        inset.set_facecolor(PANEL)
        inset.grid(True, color=GRID, linewidth=0.6, alpha=0.8)
        inset.tick_params(colors=MUTED, labelsize=6)
        inset.locator_params(nbins=4)
        inset.ticklabel_format(useOffset=False)
        for spine in inset.spines.values():
            spine.set_color(MINT)
            spine.set_linewidth(1.2)
        inset.scatter(xs, ys, c=CYAN, s=20, zorder=3)
        for r, color, ls, _, _ in specs:
            if r.p1 is not None:
                inset.plot([r.p1[0], r.p2[0]], [r.p1[1], r.p2[1]], color=color,
                           linestyle=ls, linewidth=2.5, marker="o", markersize=6,
                           markeredgecolor=BG, markeredgewidth=0.8,
                           zorder=6 if color == AMBER else 5)
        inset.set_xlim(cx - half, cx + half)
        inset.set_ylim(cy - half, cy + half)
        inset.set_title("zoom on closest pair", color=MINT, fontsize=7, pad=3)
        ax.indicate_inset_zoom(inset, edgecolor=MINT)

    ax.set_title("POINT FIELD  /  CLOSEST-PAIR DETECTION", color=TEXT, fontsize=13,
                 fontweight="bold", loc="left", pad=16)
    ax.set_xlabel("X coordinate", labelpad=9)
    ax.set_ylabel("Y coordinate", labelpad=9)
    ax.legend(loc="upper left", facecolor=PANEL, edgecolor=GRID, labelcolor=TEXT,
              fontsize=8, framealpha=0.97)
    fig.suptitle("ALGORITHM LAB     /     CLOSEST PAIR OF POINTS", color=TEXT,
                 fontsize=16, fontweight="bold", x=0.06, ha="left", y=0.96)
    fig.text(0.06, 0.905,
             "BRUTE FORCE  ×  DIVIDE AND CONQUER     •     COMPARATIVE ANALYSIS",
             color=MUTED, fontsize=9)
    agree = distances_agree(brute, dc)
    if ref.p1 is not None:
        ax.text(0.99, 0.985,
                f"SHORTEST DISTANCE  d = {ref.distance:.6f}\n"
                f"{fmt_point(ref.p1)}  ↔  {fmt_point(ref.p2)}",
                transform=ax.transAxes, ha="right", va="top", color=MINT,
                fontsize=10, fontweight="bold", zorder=10,
                bbox=dict(boxstyle="round,pad=0.5", facecolor=BG,
                          edgecolor=MINT, alpha=0.97))
    fig.text(0.06, 0.045,
             "VERIFIED  ·  BOTH ALGORITHMS AGREE" if agree else "WARNING  ·  RESULTS DIFFER",
             color=MINT if agree else PINK, fontsize=10, fontweight="bold")
    fig.text(0.97, 0.045, "PINK: BRUTE FORCE   AMBER (dashed): DIVIDE & CONQUER",
             color=MUTED, fontsize=8, ha="right")
    fig.savefig("closest_pair.png", dpi=180, facecolor=fig.get_facecolor())
    print("Saved point plot as closest_pair.png")


# --------------------------------------------------------------------------
# Optional animation of recursive splitting / merging
# --------------------------------------------------------------------------
def animate_recursion(points: List[Point], trace, delay: float = 0.65,
                      save_gif: bool = True):
    """Step-through animation of recursive splitting and merging.
    Plays live, then saves the same frames as recursion.gif."""
    if not points or not trace:
        print("Animation skipped: nothing to animate.")
        return
    fig, ax = plt.subplots(figsize=(9, 6.5), facecolor=BG)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xpad = max((max(xs) - min(xs)) * 0.06, 1)
    ypad = max((max(ys) - min(ys)) * 0.06, 1)
    titles = {"split": "DIVIDE", "base": "BASE CASE (brute force)",
              "merge": "MERGE: build strip", "merged": "MERGE: strip scanned"}

    def draw(index):
        ev = trace[index]
        ax.clear()
        style_axis(ax)
        ax.scatter(xs, ys, c=CYAN, s=23, alpha=0.42, edgecolors="none",
                   label="All points")
        cur = ev["points"]
        ax.scatter([p[0] for p in cur], [p[1] for p in cur], c=VIOLET, s=38,
                   alpha=0.95, edgecolors=TEXT, linewidths=0.25,
                   label=f"Active subproblem (depth {ev['depth']})", zorder=4)
        if ev["kind"] in ("merge", "merged"):
            mid_x, d = ev["mid_x"], ev["d"]
            ax.axvline(mid_x, color=MINT, linestyle="--", linewidth=1.6,
                       label="Divide line")
            ax.add_patch(Rectangle((mid_x - d, min(ys)), 2 * d,
                                   max(max(ys) - min(ys), 1e-9), facecolor=VIOLET,
                                   alpha=0.15, edgecolor=VIOLET, linestyle="--",
                                   label="Strip · 2d"))
            if ev["strip"]:
                ax.scatter([p[0] for p in ev["strip"]], [p[1] for p in ev["strip"]],
                           c=AMBER, s=52, edgecolors=BG, linewidths=0.6,
                           label="Strip candidates", zorder=5)
        r = ev.get("result")
        if r is not None and r.p1 is not None:
            ax.plot([r.p1[0], r.p2[0]], [r.p1[1], r.p2[1]], color=PINK,
                    linewidth=2.6, marker="o", markersize=6,
                    label=f"Best pair so far (d={r.distance:.4f})", zorder=7)
        ax.set_xlim(min(xs) - xpad, max(xs) + xpad)
        ax.set_ylim(min(ys) - ypad, max(ys) + ypad)
        ax.set_xlabel("X coordinate", labelpad=8)
        ax.set_ylabel("Y coordinate", labelpad=8)
        ax.set_title(f"STEP {index + 1:03d}/{len(trace):03d}  /  {titles[ev['kind']]}",
                     color=TEXT, fontsize=11, fontweight="bold", loc="left", pad=12)
        ax.legend(loc="upper left", facecolor=PANEL, edgecolor=GRID,
                  labelcolor=TEXT, fontsize=8)

    # Live playback
    plt.ion()
    plt.show(block=False)
    for i in range(len(trace)):
        if not plt.fignum_exists(fig.number):
            break
        draw(i)
        fig.canvas.draw_idle()
        plt.pause(delay)
    plt.ioff()

    # Save the same frames as a GIF
    if save_gif:
        try:
            from matplotlib.animation import FuncAnimation, PillowWriter
            anim = FuncAnimation(fig, draw, frames=len(trace), repeat=False)
            anim.save("recursion.gif", writer=PillowWriter(fps=2), dpi=80,
                      savefig_kwargs={"facecolor": BG})
            print("Saved recursion animation as recursion.gif")
        except Exception as exc:  # e.g. Pillow missing
            print(f"GIF not saved ({exc}); install it with: pip install pillow")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Closest pair: brute force vs divide and conquer")
    ap.add_argument("--n", type=int, help="number of points (otherwise read from stdin)")
    ap.add_argument("--seed", type=int, default=None, help="seed for repeatable points")
    ap.add_argument("--int", dest="integer", action="store_true",
                    help="integer coordinates instead of floating point")
    ap.add_argument("--range", type=int, default=100, dest="span",
                    help="coordinates are drawn from [0, RANGE] (default 100)")
    ap.add_argument("--show-points", action="store_true", help="print generated points")
    ap.add_argument("--animate", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--no-animate", action="store_true",
                    help="skip the recursion animation (on by default)")
    ap.add_argument("--no-gif", action="store_true", help="do not save recursion.gif")
    ap.add_argument("--delay", type=float, default=0.65,
                    help="seconds per animation step (default 0.65)")
    ap.add_argument("--no-plot", action="store_true", help="skip the point-field plot")
    ap.add_argument("--no-benchmark", action="store_true", help="skip the time-vs-N graph")
    ap.add_argument("--no-selftest", action="store_true", help="skip randomized verification")
    ap.add_argument("--no-show", action="store_true",
                    help="save PNGs but do not open plot windows")
    args = ap.parse_args()

    if args.n is None:
        try:
            n = int(input("Enter N (number of points): ").strip())
        except (ValueError, EOFError):
            sys.exit("Invalid input: N must be an integer.")
    else:
        n = args.n
    if n < 0:
        sys.exit("N cannot be negative.")

    points = random_points(n, args.seed, args.integer, args.span)

    # Time both algorithms without tracing overhead.
    brute, brute_ms = time_algorithm(brute_force, points)
    dc, dc_ms = time_algorithm(closest_pair_divide_conquer, points)

    # ---- required output: exactly three lines first ----
    print(format_result("Brute-Force", brute))
    print(format_result("Divide-and-Conquer", dc))
    print(f"Execution time: Brute-Force = {brute_ms:.6f} ms, "
          f"Divide-and-Conquer = {dc_ms:.6f} ms")

    # ---- supplementary output ----
    print()
    print("=" * 60)
    print("SHORTEST DISTANCE SUMMARY")
    print("=" * 60)
    if dc.p1 is None:
        print("No pair exists (fewer than 2 points).")
    else:
        print(f"Shortest distance : {dc.distance:.6f}")
        print(f"Closest pair      : {fmt_point(dc.p1)}  and  {fmt_point(dc.p2)}")
        print(f"Brute-Force found : {brute.distance:.6f}   "
              f"Divide-and-Conquer found : {dc.distance:.6f}")
    print("=" * 60)
    limit = n if (args.show_points or n <= 100) else 20
    print(f"\nGenerated {n} point(s)" +
          ("" if limit == n else f" (showing first {limit}; use --show-points for all)") + ":")
    for i, p in enumerate(points[:limit], 1):
        print(f"  P{i}: {fmt_point(p)}")
    print()
    if distances_agree(brute, dc):
        print("Verification: PASS - both algorithms report the same minimum distance")
    else:
        print("Verification: FAIL - minimum distances differ")
        raise AssertionError(f"Disagreement: {brute} vs {dc}")
    if not args.no_selftest:
        count = run_self_tests()
        print(f"Self-test: {count} cases (corner cases + random stress), all agree")

    if n >= 1 and not args.no_plot:
        trace = []
        closest_pair_divide_conquer(points, trace=trace)  # separate traced run
        plot_points(points, brute, dc, trace)
        if not args.no_animate:
            anim_trace = trace
            if n > 80:  # keep large inputs readable: show only the top recursion levels
                anim_trace = [e for e in trace if e["depth"] <= 3]
                print("Animation: N > 80, showing recursion depth 0-3 only.")
            animate_recursion(points, anim_trace, delay=args.delay,
                              save_gif=not args.no_gif)
    elif n < 1:
        print("Skipping point plot: there are no points.")

    if not args.no_benchmark:
        performance_analysis(seed=args.seed if args.seed is not None else 1234,
                             integer=args.integer)

    if not args.no_show:
        plt.show()


if __name__ == "__main__":
    main()