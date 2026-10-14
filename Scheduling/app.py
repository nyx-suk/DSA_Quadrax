#!/usr/bin/env python3
"""
Exam Timetable Scheduling Web App (Flask Backend)
Provides REST API endpoints for:
- Solving timetabling instances (Option 1 manual text / Option 2 random graph)
- Generating step-by-step animation sequences
- Benchmarking performance across increasing N
- Exporting CSV timetables
"""

import io
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from flask import Flask, jsonify, render_template, request, send_file
import networkx as nx
import numpy as np

# Import core algorithms
import exam_scheduler as core

app = Flask(__name__)

# Preset samples for quick testing
PRESETS = {
    "small": {
        "name": "Small University (12 Courses, R=3)",
        "r": 3,
        "text": """12 18 3
1 2
1 3
2 4
2 5
3 6
4 7
5 7
6 8
7 9
8 10
9 11
10 12
11 12
3 7
2 8
5 9
4 10
1 12"""
    },
    "medium": {
        "name": "Departmental Exams (20 Courses, R=4)",
        "r": 4,
        "text": """20 32 4
1 2
1 5
2 3
2 6
3 4
3 7
4 8
5 6
5 9
6 7
6 10
7 8
7 11
8 12
9 10
9 13
10 11
10 14
11 12
11 15
12 16
13 14
13 17
14 15
14 18
15 16
15 19
16 20
17 18
18 19
19 20
1 20"""
    },
    "dense": {
        "name": "High Conflict Challenge (15 Courses, R=3, Dense)",
        "r": 3,
        "text": """15 36 3
1 2
1 3
1 4
1 5
2 3
2 6
2 7
3 4
3 8
4 5
4 9
5 10
6 7
6 11
7 8
7 12
8 9
8 13
9 10
9 14
10 15
11 12
11 13
12 14
13 15
1 15
2 14
3 13
4 12
5 11
6 10
7 9
8 14
9 15
2 11
3 10"""
    }
}


def parse_text_input(raw_text: str) -> Tuple[nx.Graph, int, int, int]:
    """Parse text into a NetworkX Graph and parameters N, M, R."""
    lines = [l.strip() for l in raw_text.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
    if not lines:
        raise ValueError("Input cannot be empty.")
    
    header = lines[0].split()
    if len(header) < 3:
        raise ValueError("First line must contain: N M R")
    
    N, M, R = int(header[0]), int(header[1]), int(header[2])
    G = nx.Graph()
    G.add_nodes_from(range(1, N + 1))
    
    for line in lines[1: M + 1]:
        parts = line.split()
        if len(parts) >= 2:
            u, v = int(parts[0]), int(parts[1])
            if u != v:
                G.add_edge(u, v)
                
    return G, N, G.number_of_edges(), R


@app.route("/")
def index():
    """Render the main single page visualizer."""
    return render_template("index.html")


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Return available preset graph inputs."""
    return jsonify(PRESETS)


@app.route("/api/solve", methods=["POST"])
def solve():
    """
    Main solve endpoint:
    Accepts mode ('file' | 'generate') and parameters.
    Runs Welsh-Powell, DSatur, and Exact Branch & Bound.
    Returns structured results, timetable grid, animation steps, and graph structure.
    """
    try:
        data = request.get_json() or {}
        mode = data.get("mode", "file")
        time_limit = float(data.get("time_limit", 15.0))

        if mode == "file":
            raw_text = data.get("text", "")
            G, N, M, R = parse_text_input(raw_text)
        elif mode == "generate":
            N = int(data.get("n", 15))
            R = int(data.get("r", 4))
            density = float(data.get("density", 0.25))
            G, N, M, R = core.generate_random_conflict_graph(N, R, density)
        else:
            return jsonify({"success": False, "error": f"Unknown mode: {mode}"}), 400

        lower_bound = core.calculate_lower_bound(G, R)

        # 1. Run Welsh-Powell with step snapshots
        wp_assign, wp_slots, wp_time, wp_steps = core.welsh_powell_coloring(G, R, record_snapshots=True)

        # 2. Run DSatur with step snapshots
        ds_assign, ds_slots, ds_time, ds_steps = core.dsatur_coloring(G, R, record_snapshots=True)

        # 3. Run Exact Branch-and-Bound
        initial_ub = min(wp_slots, ds_slots)
        heuristic_assign = ds_assign if ds_slots <= wp_slots else wp_assign
        ex_assign, ex_slots, ex_optimal, ex_time = core.exact_branch_and_bound(
            G, R, initial_ub, initial_assignment=heuristic_assign, time_limit=time_limit
        )

        # Choose best solution
        if ex_optimal and ex_assign:
            best_method = "exact"
            best_assign = ex_assign
            best_slots = ex_slots
            is_optimal = True
        elif ds_slots <= wp_slots:
            best_method = "dsatur"
            best_assign = ds_assign
            best_slots = ds_slots
            is_optimal = (best_slots == lower_bound)
        else:
            best_method = "welsh_powell"
            best_assign = wp_assign
            best_slots = wp_slots
            is_optimal = (best_slots == lower_bound)

        # Slot-wise map
        slot_map = defaultdict(list)
        for course, slot in best_assign.items():
            slot_map[slot].append(course)

        slot_wise_courses = {
            f"Slot {s + 1}": sorted(slot_map[s]) for s in range(best_slots)
        }

        # Timetable Grid data: rows = slots, cols = halls (1..R)
        grid_rows = []
        for s in range(best_slots):
            courses = sorted(slot_map[s])
            row = {
                "slot_index": s,
                "slot_label": f"Slot {s + 1}",
                "courses": courses,
                "halls": [courses[i] if i < len(courses) else None for i in range(R)]
            }
            grid_rows.append(row)

        # Prepare Graph representation for Vis.js
        nodes_data = []
        for v in sorted(G.nodes()):
            slot_idx = best_assign.get(v, 0)
            nodes_data.append({
                "id": v,
                "label": f"C{v}",
                "title": f"Course {v}<br>Assigned: Slot {slot_idx + 1}<br>Conflicts: {G.degree[v]}",
                "degree": G.degree[v],
                "slot": slot_idx
            })

        edges_data = [{"from": u, "to": v} for u, v in G.edges()]

        # Generate CSV representation
        csv_lines = [",".join(["Slot"] + [f"Hall {i + 1}" for i in range(R)])]
        for s in range(best_slots):
            courses = sorted(slot_map[s])
            row_items = [f"Slot {s + 1}"] + [str(c) for c in courses] + [""] * (R - len(courses))
            csv_lines.append(",".join(row_items))
        csv_content = "\n".join(csv_lines)

        # Prepare animation snapshots from DSatur
        animation_steps = []
        for step_idx, snap in enumerate(ds_steps):
            # Find which node was just assigned
            latest_node = list(snap.keys())[-1]
            animation_steps.append({
                "step": step_idx + 1,
                "course": latest_node,
                "slot": snap[latest_node],
                "assignment": {str(k): v for k, v in snap.items()}
            })

        response_payload = {
            "success": True,
            "n": N,
            "m": M,
            "r": R,
            "lower_bound": lower_bound,
            "best_method": best_method,
            "best_slots": best_slots,
            "is_optimal": is_optimal,
            "algorithms": {
                "welsh_powell": {
                    "name": "Greedy (Welsh-Powell)",
                    "slots": wp_slots,
                    "runtime": round(wp_time, 5),
                    "proven_optimal": False,
                    "assignment": {str(k): v for k, v in wp_assign.items()}
                },
                "dsatur": {
                    "name": "Greedy (DSatur)",
                    "slots": ds_slots,
                    "runtime": round(ds_time, 5),
                    "proven_optimal": False,
                    "assignment": {str(k): v for k, v in ds_assign.items()}
                },
                "exact": {
                    "name": "Exact (Branch & Bound)",
                    "slots": ex_slots,
                    "runtime": round(ex_time, 5),
                    "proven_optimal": ex_optimal,
                    "assignment": {str(k): v for k, v in ex_assign.items()} if ex_assign else {}
                }
            },
            "slot_wise_courses": slot_wise_courses,
            "grid_rows": grid_rows,
            "graph": {
                "nodes": nodes_data,
                "edges": edges_data
            },
            "animation_steps": animation_steps,
            "csv_content": csv_content
        }
        return jsonify(response_payload)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/benchmark", methods=["POST"])
def run_benchmark():
    """
    Run comparison across increasing N values.
    Returns datapoints for Welsh-Powell, DSatur, and Exact Branch & Bound.
    """
    try:
        data = request.get_json() or {}
        r = int(data.get("r", 4))
        density = float(data.get("density", 0.25))
        n_values = data.get("n_values", [8, 12, 16, 20, 24, 28, 32])

        wp_slots, wp_times = [], []
        ds_slots, ds_times = [], []
        ex_slots, ex_times = [], []

        for n in n_values:
            G_bench = nx.Graph()
            G_bench.add_nodes_from(range(1, n + 1))
            for u in range(1, n + 1):
                for v in range(u + 1, n + 1):
                    if random.random() < density:
                        G_bench.add_edge(u, v)

            # WP
            _, w_s, w_t, _ = core.welsh_powell_coloring(G_bench, r)
            wp_slots.append(w_s)
            wp_times.append(round(w_t, 6))

            # DSatur
            _, d_s, d_t, _ = core.dsatur_coloring(G_bench, r)
            ds_slots.append(d_s)
            ds_times.append(round(d_t, 6))

            # Exact B&B (capped at 4s per instance)
            ub = min(w_s, d_s)
            _, e_s, _, e_t = core.exact_branch_and_bound(G_bench, r, ub, time_limit=4.0)
            ex_slots.append(e_s)
            ex_times.append(round(e_t, 6))

        return jsonify({
            "success": True,
            "n_values": n_values,
            "r": r,
            "density": density,
            "results": {
                "welsh_powell": {"slots": wp_slots, "times": wp_times},
                "dsatur": {"slots": ds_slots, "times": ds_times},
                "exact": {"slots": ex_slots, "times": ex_times}
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/download_csv", methods=["POST"])
def download_csv():
    """Allow browser to download generated CSV timetable."""
    data = request.get_json() or {}
    csv_text = data.get("csv_content", "")
    buffer = io.BytesIO()
    buffer.write(csv_text.encode("utf-8"))
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="text/csv",
        as_attachment=True,
        download_name="exam_timetable.csv"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"Starting Exam Scheduler Web Visualizer on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
