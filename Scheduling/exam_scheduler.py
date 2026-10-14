#!/usr/bin/env python3
"""
Exam Timetable Scheduling (Graph Colouring Challenge)
=====================================================
Problem 4:
A university has N courses. Two courses conflict if at least one student is
enrolled in both, so they cannot be scheduled in the same time slot.
In addition, at most R exams can be held in any single slot (hall capacity constraint).
Assign every course to a time slot to minimize total slots while satisfying conflicts
and capacity limits.

Algorithms implemented:
1. Greedy Heuristic 1: Welsh-Powell (with capacity constraint R)
2. Greedy Heuristic 2: DSatur (with capacity constraint R)
3. Exact Method: Backtracking with Branch-and-Bound (symmetry breaking & pruning)

Outputs:
- Output 1: Minimum number of slots (for each algorithm), along with optimality status.
- Output 2: Slot-wise list of courses (e.g., Slot 1: 2, 5, 9).
- Output 3: CSV file with the timetable (rows = slots, columns = exam positions/halls).
- Visualizations:
  * Conflict graph with nodes coloured according to their assigned slot.
  * Final timetable as a grid, with the same colour scheme as the graph.
  * Comparison chart of slots used and running time as N increases.
  * Animation of the course-to-slot assignment order (GIF).
"""

import argparse
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib import animation

# Set random seed for reproducibility
random.seed(42)
np.random.seed(42)

# Ensure matplotlib uses a non-GUI backend when running in scripts/headless
plt.switch_backend("Agg")


# =====================================================================
# Graph Construction & Input Parsing
# =====================================================================

def parse_input_file(filepath: Path) -> Tuple[nx.Graph, int, int, int]:
    """
    Parses Option 1 input:
    First line: N M R
    Next M lines: u v (1-based course indices)
    Returns: (Graph, N, M, R)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not lines:
        raise ValueError("Input file is empty.")

    header = lines[0].split()
    if len(header) < 3:
        raise ValueError("First line must contain: N M R")

    N, M, R = int(header[0]), int(header[1]), int(header[2])
    G = nx.Graph()
    G.add_nodes_from(range(1, N + 1))

    for line in lines[1 : M + 1]:
        parts = line.split()
        if len(parts) >= 2:
            u, v = int(parts[0]), int(parts[1])
            if u != v:
                G.add_edge(u, v)

    return G, N, G.number_of_edges(), R


def generate_random_conflict_graph(N: int, R: int, density: float) -> Tuple[nx.Graph, int, int, int]:
    """
    Generates Option 2 input:
    Random graph with N courses, hall capacity R, and user-specified edge density in [0, 1].
    Returns: (Graph, N, M, R)
    """
    G = nx.Graph()
    G.add_nodes_from(range(1, N + 1))
    for u in range(1, N + 1):
        for v in range(u + 1, N + 1):
            if random.random() < density:
                G.add_edge(u, v)
    return G, N, G.number_of_edges(), R


# =====================================================================
# Lower Bound Estimation
# =====================================================================

def calculate_lower_bound(G: nx.Graph, R: int) -> int:
    """
    Theoretical lower bounds:
    1. Capacity bound: ceil(N / R)
    2. Max degree bound: max_degree + 1 (for local clique-like behavior)
    3. Clique bound: size of maximum clique found by heuristic approximation
    """
    N = G.number_of_nodes()
    if N == 0:
        return 0
    cap_bound = (N + R - 1) // R
    max_deg = max(dict(G.degree()).values()) if N > 0 else 0
    
    # Heuristic clique size via networkx
    try:
        clique_size = len(nx.algorithms.clique.max_weight_clique(G, weight=None)[0])
    except Exception:
        clique_size = 1

    return max(cap_bound, clique_size)


# =====================================================================
# 1. Greedy Heuristic: Welsh-Powell (Capacitated)
# =====================================================================

def welsh_powell_coloring(
    G: nx.Graph, R: int, record_snapshots: bool = False
) -> Tuple[Dict[int, int], int, float, List[Dict[int, int]]]:
    """
    Welsh-Powell Algorithm with Hall Capacity Constraint:
    1. Sort vertices by degree in descending order.
    2. Greedily assign the lowest feasible slot s >= 0 such that:
       - No adjacent vertex is in slot s.
       - The number of vertices already in slot s is < R.
    """
    start_time = time.perf_counter()
    # Sort nodes by degree descending, then by node id ascending
    sorted_nodes = sorted(G.nodes(), key=lambda v: (G.degree[v], -v), reverse=True)
    assignment: Dict[int, int] = {}
    slot_counts: Dict[int, int] = defaultdict(int)
    snapshots: List[Dict[int, int]] = []

    for node in sorted_nodes:
        # Find neighboring used slots
        neighbor_slots = {assignment[nbr] for nbr in G.neighbors(node) if nbr in assignment}
        slot = 0
        while True:
            if slot not in neighbor_slots and slot_counts[slot] < R:
                break
            slot += 1
        assignment[node] = slot
        slot_counts[slot] += 1
        if record_snapshots:
            snapshots.append(dict(assignment))

    runtime = time.perf_counter() - start_time
    total_slots = max(assignment.values()) + 1 if assignment else 0
    return assignment, total_slots, runtime, snapshots


# =====================================================================
# 2. Greedy Heuristic: DSatur (Capacitated)
# =====================================================================

def dsatur_coloring(
    G: nx.Graph, R: int, record_snapshots: bool = False
) -> Tuple[Dict[int, int], int, float, List[Dict[int, int]]]:
    """
    DSatur (Degree of Saturation) Algorithm with Hall Capacity Constraint:
    1. Saturation degree = number of distinct colors assigned to neighbors.
    2. At each step, select uncolored vertex with highest saturation degree.
       Tie-break by highest degree in the uncolored graph (or original degree).
    3. Assign lowest available slot s >= 0 respecting conflicts and hall capacity R.
    """
    start_time = time.perf_counter()
    nodes = list(G.nodes())
    uncolored = set(nodes)
    assignment: Dict[int, int] = {}
    slot_counts: Dict[int, int] = defaultdict(int)
    snapshots: List[Dict[int, int]] = []

    initial_degrees = dict(G.degree())

    while uncolored:
        # Compute saturation for uncolored vertices
        best_cand = None
        best_sat = -1
        best_deg = -1

        for v in uncolored:
            nbr_colors = {assignment[nbr] for nbr in G.neighbors(v) if nbr in assignment}
            sat = len(nbr_colors)
            deg = initial_degrees[v]
            if (sat > best_sat) or (sat == best_sat and deg > best_deg):
                best_sat = sat
                best_deg = deg
                best_cand = v

        cand = best_cand
        # Find lowest valid slot
        neighbor_slots = {assignment[nbr] for nbr in G.neighbors(cand) if nbr in assignment}
        slot = 0
        while True:
            if slot not in neighbor_slots and slot_counts[slot] < R:
                break
            slot += 1

        assignment[cand] = slot
        slot_counts[slot] += 1
        uncolored.remove(cand)

        if record_snapshots:
            snapshots.append(dict(assignment))

    runtime = time.perf_counter() - start_time
    total_slots = max(assignment.values()) + 1 if assignment else 0
    return assignment, total_slots, runtime, snapshots


# =====================================================================
# 3. Exact Method: Backtracking with Branch-and-Bound
# =====================================================================

def exact_branch_and_bound(
    G: nx.Graph, R: int, initial_upper_bound: int, time_limit: float = 15.0
) -> Tuple[Dict[int, int], int, bool, float]:
    """
    Exact Branch-and-Bound solver for Capacitated Graph Coloring:
    - Pruning 1: used_slots >= best_slots -> backtrack
    - Pruning 2: used_slots + ceil((unassigned_nodes) / R) >= best_slots -> backtrack
    - Pruning 3: Symmetry breaking (only branch on one new empty slot)
    - Early exit: If best_slots reaches theoretical lower bound, search terminates immediately.
    """
    start_time = time.perf_counter()
    nodes = sorted(G.nodes(), key=lambda v: G.degree[v], reverse=True)
    n = len(nodes)
    if n == 0:
        return {}, 0, True, 0.0

    lower_bound = calculate_lower_bound(G, R)
    best_slots = initial_upper_bound
    best_assignment: Dict[int, int] = {}
    timed_out = False

    # Precompute neighbors as indices
    node_to_idx = {v: i for i, v in enumerate(nodes)}
    adj_list = [[node_to_idx[nbr] for nbr in G.neighbors(v)] for v in nodes]

    current_assign = [-1] * n
    slot_sizes = [0] * n  # max slots could be n

    def dfs(idx: int, current_used_slots: int):
        nonlocal best_slots, best_assignment, timed_out

        if time.perf_counter() - start_time > time_limit:
            timed_out = True
            return

        if idx == n:
            if current_used_slots < best_slots:
                best_slots = current_used_slots
                best_assignment = {nodes[i]: current_assign[i] for i in range(n)}
            return

        # Pruning 1: Already at or exceeding best known slots
        if current_used_slots >= best_slots:
            return

        # Pruning 2: Theoretical remaining slots lower bound
        remaining_nodes = n - idx
        min_extra_slots = (remaining_nodes + R - 1) // R
        if current_used_slots + min_extra_slots >= best_slots:
            return

        # Find which slots are forbidden by neighbors
        forbidden = set()
        for nbr_idx in adj_list[idx]:
            s = current_assign[nbr_idx]
            if s != -1:
                forbidden.add(s)

        # Try existing non-empty slots first
        for s in range(current_used_slots):
            if s not in forbidden and slot_sizes[s] < R:
                current_assign[idx] = s
                slot_sizes[s] += 1
                dfs(idx + 1, current_used_slots)
                slot_sizes[s] -= 1
                current_assign[idx] = -1

                if best_slots == lower_bound:
                    return
                if timed_out:
                    return

        # Try opening ONE new slot (symmetry breaking)
        new_slot = current_used_slots
        if new_slot < best_slots:
            current_assign[idx] = new_slot
            slot_sizes[new_slot] += 1
            dfs(idx + 1, current_used_slots + 1)
            slot_sizes[new_slot] -= 1
            current_assign[idx] = -1

    dfs(0, 0)
    elapsed = time.perf_counter() - start_time
    is_optimal = (not timed_out) or (best_slots == lower_bound)
    return best_assignment, best_slots, is_optimal, elapsed


# =====================================================================
# Output 2 & 3 Helpers
# =====================================================================

def format_slot_wise_courses(assignment: Dict[int, int]) -> str:
    """Format slot-wise list of courses: Slot 1: 2, 5, 9..."""
    slot_map = defaultdict(list)
    for course, slot in assignment.items():
        slot_map[slot].append(course)

    lines = []
    for s in sorted(slot_map.keys()):
        courses_str = ", ".join(map(str, sorted(slot_map[s])))
        lines.append(f"Slot {s + 1}: {courses_str}")
    return "\n".join(lines)


def save_timetable_csv(assignment: Dict[int, int], R: int, out_csv_path: Path):
    """
    Output 3: CSV file with the timetable
    Rows = slots, Columns = exam positions / halls
    """
    slot_map = defaultdict(list)
    for course, slot in assignment.items():
        slot_map[slot].append(course)

    rows = []
    slot_labels = []
    for s in sorted(slot_map.keys()):
        courses = sorted(slot_map[s])
        # Pad with empty string if fewer than R exams in slot
        row = courses + [""] * (R - len(courses))
        rows.append(row)
        slot_labels.append(f"Slot {s + 1}")

    col_names = [f"Hall {i + 1}" for i in range(R)]
    df = pd.DataFrame(rows, columns=col_names, index=slot_labels)
    df.index.name = "Slot"
    df.to_csv(out_csv_path)
    return df


# =====================================================================
# Visualizations
# =====================================================================

def get_slot_colormap(num_slots: int):
    """
    Returns a distinct list of RGBA colors for slots so both the graph
    and the timetable grid share the exact same consistent palette.
    """
    if num_slots <= 10:
        base_cmap = plt.get_cmap("tab10")
    elif num_slots <= 20:
        base_cmap = plt.get_cmap("tab20")
    else:
        base_cmap = plt.get_cmap("gist_rainbow")

    return [base_cmap(i % base_cmap.N) for i in range(num_slots)]


def draw_conflict_graph(
    G: nx.Graph,
    assignment: Dict[int, int],
    num_slots: int,
    out_path: Path,
    title: str = "Conflict Graph (Coloured by Exam Slot)",
):
    """
    Visualisation 1:
    Draw the conflict graph with nodes coloured according to their assigned slot.
    Includes a legend mapping slot numbers to colors.
    """
    colors_palette = get_slot_colormap(num_slots)
    node_colors = [colors_palette[assignment[node]] for node in G.nodes()]

    plt.figure(figsize=(9, 7))
    pos = nx.spring_layout(G, seed=42, k=1.0 / np.sqrt(max(1, G.number_of_nodes())))

    # Draw edges
    nx.draw_networkx_edges(G, pos, alpha=0.35, edge_color="gray", width=1.2)

    # Draw nodes
    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        node_size=650,
        edgecolors="black",
        linewidths=1.5,
    )

    # Draw labels
    nx.draw_networkx_labels(
        G,
        pos,
        font_size=10,
        font_weight="bold",
        font_color="black",
    )

    # Build legend for slots
    legend_handles = []
    for s in range(num_slots):
        patch = plt.Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=f"Slot {s + 1}",
            markerfacecolor=colors_palette[s],
            markersize=11,
            markeredgecolor="black",
        )
        legend_handles.append(patch)

    plt.legend(
        handles=legend_handles,
        title="Exam Slots",
        bbox_to_anchor=(1.03, 1),
        loc="upper left",
        frameon=True,
    )
    plt.title(title, fontsize=14, fontweight="bold", pad=12)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def draw_timetable_grid(
    assignment: Dict[int, int],
    R: int,
    num_slots: int,
    out_path: Path,
):
    """
    Visualisation 2:
    Show the final timetable as a grid, with the EXACT SAME colour scheme as the graph.
    Rows = slots, Columns = Halls/Positions.
    """
    colors_palette = get_slot_colormap(num_slots)

    slot_map = defaultdict(list)
    for course, slot in assignment.items():
        slot_map[slot].append(course)

    rows = []
    slot_labels = []
    cell_colors = []

    for s in range(num_slots):
        courses = sorted(slot_map[s])
        row_text = []
        row_colors = []
        base_color = colors_palette[s]

        # Use slightly lightened color for cell fill, and dark text
        fill_color = (*base_color[:3], 0.65)  # 65% opacity

        for i in range(R):
            if i < len(courses):
                row_text.append(f"Course {courses[i]}")
                row_colors.append(fill_color)
            else:
                row_text.append("—")
                row_colors.append((0.95, 0.95, 0.95, 1.0))  # Light grey for empty hall

        rows.append(row_text)
        slot_labels.append(f"Slot {s + 1}")
        cell_colors.append(row_colors)

    col_labels = [f"Hall {i + 1}" for i in range(R)]

    fig_height = max(4.0, num_slots * 0.7 + 1.8)
    fig_width = max(6.0, R * 2.2 + 2.0)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.axis("off")

    table = ax.table(
        cellText=rows,
        rowLabels=slot_labels,
        colLabels=col_labels,
        cellColours=cell_colors,
        loc="center",
        cellLoc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.8)

    # Style header cells
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("black")
        cell.set_linewidth(1.0)
        if r == 0:  # Column header
            cell.set_facecolor("#2b3e50")
            cell.set_text_props(color="white", weight="bold")
        elif c == -1:  # Row header
            slot_idx = r - 1
            slot_color = colors_palette[slot_idx]
            cell.set_facecolor(slot_color)
            # Choose text color based on brightness
            luminance = 0.299 * slot_color[0] + 0.587 * slot_color[1] + 0.114 * slot_color[2]
            text_color = "black" if luminance > 0.5 else "white"
            cell.set_text_props(color=text_color, weight="bold")

    plt.title(
        f"Final Exam Timetable Grid (Capacity R={R} per Slot)",
        fontsize=14,
        fontweight="bold",
        pad=18,
    )
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()


def generate_comparison_chart_as_N_increases(
    R: int,
    density: float,
    out_path: Path,
    n_values: Optional[List[int]] = None,
):
    """
    Visualisation 3:
    Show a comparison chart of slots used and running time for each algorithm as N increases.
    """
    if n_values is None:
        n_values = [8, 12, 16, 20, 24, 28, 32]

    wp_slots_list, wp_time_list = [], []
    ds_slots_list, ds_time_list = [], []
    ex_slots_list, ex_time_list = [], []

    print("\nRunning benchmark across varying N to generate comparison chart...")
    for n in n_values:
        # Generate random graph for benchmark
        G_bench = nx.Graph()
        G_bench.add_nodes_from(range(1, n + 1))
        for u in range(1, n + 1):
            for v in range(u + 1, n + 1):
                if random.random() < density:
                    G_bench.add_edge(u, v)

        # Welsh-Powell
        _, wp_slots, wp_time, _ = welsh_powell_coloring(G_bench, R)
        wp_slots_list.append(wp_slots)
        wp_time_list.append(wp_time)

        # DSatur
        _, ds_slots, ds_time, _ = dsatur_coloring(G_bench, R)
        ds_slots_list.append(ds_slots)
        ds_time_list.append(ds_time)

        # Exact B&B (capped at 5s per test during benchmark)
        ub = min(wp_slots, ds_slots)
        _, ex_slots, _, ex_time = exact_branch_and_bound(G_bench, R, ub, time_limit=5.0)
        ex_slots_list.append(ex_slots)
        ex_time_list.append(ex_time)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))

    # Subplot 1: Slots Used vs N
    ax1.plot(n_values, wp_slots_list, "o--", label="Welsh-Powell (Greedy)", color="#e67e22", linewidth=2)
    ax1.plot(n_values, ds_slots_list, "s-", label="DSatur (Greedy)", color="#2980b9", linewidth=2)
    ax1.plot(n_values, ex_slots_list, "^-.", label="Exact (Branch & Bound)", color="#27ae60", linewidth=2.2)
    ax1.set_xlabel("Number of Courses (N)", fontsize=12, fontweight="bold")
    ax1.set_ylabel("Minimum Slots Used", fontsize=12, fontweight="bold")
    ax1.set_title("Slots Used vs Number of Courses (N)", fontsize=13, fontweight="bold")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend(fontsize=10)

    # Subplot 2: Running Time vs N
    ax2.plot(n_values, wp_time_list, "o--", label="Welsh-Powell (Greedy)", color="#e67e22", linewidth=2)
    ax2.plot(n_values, ds_time_list, "s-", label="DSatur (Greedy)", color="#2980b9", linewidth=2)
    ax2.plot(n_values, ex_time_list, "^-.", label="Exact (Branch & Bound)", color="#27ae60", linewidth=2.2)
    ax2.set_yscale("log")
    ax2.set_xlabel("Number of Courses (N)", fontsize=12, fontweight="bold")
    ax2.set_ylabel("Running Time (seconds, log scale)", fontsize=12, fontweight="bold")
    ax2.set_title("Runtime vs Number of Courses (N)", fontsize=13, fontweight="bold")
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.legend(fontsize=10)

    fig.suptitle(f"Algorithm Comparison as N Increases (Hall Capacity R={R}, Density={density:.2f})", fontsize=15, fontweight="bold")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Comparison chart saved to {out_path}")


def animate_assignment_process(
    G: nx.Graph,
    snapshots: List[Dict[int, int]],
    num_slots: int,
    out_gif_path: Path,
):
    """
    Visualisation 4 (Optional):
    Animate the order in which courses are assigned to slots.
    Saves as an animated GIF.
    """
    if not snapshots:
        return

    colors_palette = get_slot_colormap(num_slots)
    pos = nx.spring_layout(G, seed=42, k=1.0 / np.sqrt(max(1, G.number_of_nodes())))

    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    def update(frame_idx):
        ax.clear()
        current_assign = snapshots[frame_idx]
        node_colors = []
        for node in G.nodes():
            if node in current_assign:
                node_colors.append(colors_palette[current_assign[node]])
            else:
                node_colors.append("#dcdde1")  # Light gray for unassigned

        nx.draw_networkx_edges(G, pos, alpha=0.3, edge_color="gray", ax=ax)
        nx.draw_networkx_nodes(
            G,
            pos,
            node_color=node_colors,
            node_size=600,
            edgecolors="black",
            linewidths=1.2,
            ax=ax,
        )
        nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", ax=ax)

        latest_node = list(current_assign.keys())[-1]
        latest_slot = current_assign[latest_node] + 1
        ax.set_title(
            f"Assignment Step {frame_idx + 1}/{len(snapshots)}: Course {latest_node} assigned to Slot {latest_slot}",
            fontsize=12,
            fontweight="bold",
        )
        ax.axis("off")

    anim = animation.FuncAnimation(fig, update, frames=len(snapshots), interval=600, repeat=False)
    anim.save(out_gif_path, writer="pillow", dpi=120)
    plt.close()
    print(f"Assignment animation saved to {out_gif_path}")


# =====================================================================
# Main Orchestration
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Exam Timetable Scheduling (Graph Colouring Challenge)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input-file", type=Path, help="Option 1: Path to input text file containing N M R and edges")
    group.add_argument(
        "--generate",
        nargs=3,
        metavar=("N", "R", "DENSITY"),
        help="Option 2: Generate random conflict graph: N, R, density (0.0 to 1.0)",
    )
    parser.add_argument("--animate", action="store_true", help="Generate animated GIF of the assignment process")
    parser.add_argument("--benchmark", action="store_true", default=True, help="Generate comparison chart as N increases")
    parser.add_argument("--time-limit", type=float, default=15.0, help="Time limit for exact solver in seconds (default: 15s)")
    args = parser.parse_args()

    # Determine input mode
    density = 0.25
    if args.input_file:
        G, N, M, R = parse_input_file(args.input_file)
        input_desc = f"File: {args.input_file} (N={N}, M={M}, R={R})"
    elif args.generate:
        N = int(args.generate[0])
        R = int(args.generate[1])
        density = float(args.generate[2])
        G, N, M, R = generate_random_conflict_graph(N, R, density)
        input_desc = f"Generated Random Graph (N={N}, M={M}, R={R}, Density={density:.2f})"
    else:
        # Default fallback sample
        N, R, density = 15, 4, 0.25
        G, N, M, R = generate_random_conflict_graph(N, R, density)
        input_desc = f"Default Random Instance (N={N}, M={M}, R={R}, Density={density:.2f})"

    print("=" * 70)
    print(" EXAM TIMETABLE SCHEDULING (GRAPH COLOURING CHALLENGE)")
    print("=" * 70)
    print(f"Configuration: {input_desc}")
    print(f"Hall Capacity per Slot (R): {R}")
    print(f"Theoretical Lower Bound on Slots: {calculate_lower_bound(G, R)}")
    print("-" * 70)

    # 1. Run Welsh-Powell
    wp_assign, wp_slots, wp_time, wp_snapshots = welsh_powell_coloring(G, R, record_snapshots=args.animate)

    # 2. Run DSatur
    ds_assign, ds_slots, ds_time, ds_snapshots = dsatur_coloring(G, R, record_snapshots=args.animate)

    # 3. Run Exact Branch-and-Bound
    initial_ub = min(wp_slots, ds_slots)
    ex_assign, ex_slots, ex_optimal, ex_time = exact_branch_and_bound(G, R, initial_ub, time_limit=args.time_limit)

    # Select the best schedule for timetable output and visualisations
    if ex_optimal and ex_assign:
        chosen_assign = ex_assign
        chosen_slots = ex_slots
        chosen_method = "Exact (Branch & Bound)"
    elif ds_slots <= wp_slots:
        chosen_assign = ds_assign
        chosen_slots = ds_slots
        chosen_method = "DSatur (Greedy)"
    else:
        chosen_assign = wp_assign
        chosen_slots = wp_slots
        chosen_method = "Welsh-Powell (Greedy)"

    # =====================================================================
    # OUTPUT 1: Minimum number of slots and optimality
    # =====================================================================
    print("\n" + "=" * 70)
    print(" OUTPUT 1: MINIMUM NUMBER OF SLOTS (BY ALGORITHM)")
    print("=" * 70)
    print(f"{'Algorithm':<28} | {'Slots Found':<12} | {'Runtime (s)':<14} | {'Proven Optimal?'}")
    print("-" * 70)
    print(f"{'Greedy (Welsh-Powell)':<28} | {wp_slots:<12} | {wp_time:<14.5f} | {'No (Heuristic)'}")
    print(f"{'Greedy (DSatur)':<28} | {ds_slots:<12} | {ds_time:<14.5f} | {'No (Heuristic)'}")
    opt_str = f"Yes (Proven Optimal)" if ex_optimal else f"No (Timed out after {args.time_limit}s)"
    print(f"{'Exact (Branch & Bound)':<28} | {ex_slots:<12} | {ex_time:<14.5f} | {opt_str}")
    print("-" * 70)
    print(f"Overall Minimum Slots Achieved: {chosen_slots} (via {chosen_method})")
    print(f"Optimality Status: {'PROVEN OPTIMAL' if (ex_optimal and chosen_slots == ex_slots) else 'HEURISTIC (Best Found)'}")

    # =====================================================================
    # OUTPUT 2: Slot-wise list of courses
    # =====================================================================
    print("\n" + "=" * 70)
    print(f" OUTPUT 2: SLOT-WISE LIST OF COURSES ({chosen_method})")
    print("=" * 70)
    print(format_slot_wise_courses(chosen_assign))

    # =====================================================================
    # OUTPUT 3: CSV file with the timetable
    # =====================================================================
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    csv_file = Path("timetable.csv")
    df_timetable = save_timetable_csv(chosen_assign, R, csv_file)
    print("\n" + "=" * 70)
    print(" OUTPUT 3: CSV TIMETABLE")
    print("=" * 70)
    print(f"Complete timetable written to: {csv_file.resolve()}")
    print("\nTimetable Preview:")
    print(df_timetable.to_string())

    # =====================================================================
    # VISUALIZATIONS
    # =====================================================================
    print("\n" + "=" * 70)
    print(" GENERATING VISUALIZATIONS")
    print("=" * 70)

    # 1. Conflict graph
    graph_img = out_dir / "conflict_graph.png"
    draw_conflict_graph(G, chosen_assign, chosen_slots, graph_img)
    print(f"1. Coloured Conflict Graph saved to : {graph_img.resolve()}")

    # 2. Timetable Grid (same colour scheme as graph)
    grid_img = out_dir / "timetable_grid.png"
    draw_timetable_grid(chosen_assign, R, chosen_slots, grid_img)
    print(f"2. Timetable Grid (matching colours): {grid_img.resolve()}")

    # 3. Comparison chart as N increases
    if args.benchmark:
        comp_img = out_dir / "comparison_as_N_increases.png"
        generate_comparison_chart_as_N_increases(R=R, density=density, out_path=comp_img)

    # 4. Optional Animation
    if args.animate:
        anim_gif = out_dir / "assignment_animation.gif"
        snapshots_to_use = ds_snapshots if ds_snapshots else wp_snapshots
        animate_assignment_process(G, snapshots_to_use, chosen_slots, anim_gif)

    print("\nExecution complete! All requested outputs and visualisations are ready.")


if __name__ == "__main__":
    main()
