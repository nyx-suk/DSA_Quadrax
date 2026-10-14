# DSA_Quadrax 🚀

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Java](https://img.shields.io/badge/Java-JDK%208%2B-orange.svg?logo=openjdk&logoColor=white)](https://www.oracle.com/java/)
[![Flask](https://img.shields.io/badge/Flask-Web%20Visualizer-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-CSS-38bdf8.svg?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**DSA_Quadrax** is a collection of four advanced algorithmic solutions developed for competitive Data Structures & Algorithms (DSA) hackathon challenges. Each project solves a classic computational optimization problem, paired with mathematical proofs, performance benchmarks, and interactive web/GUI visualizers.

---

## 📌 Table of Contents

- [Overview of Challenges](#-overview-of-challenges)
- [Module 1: Exam Timetable Scheduling (`Scheduling/`)](#-module-1-exam-timetable-scheduling-scheduling)
  - [Problem Formulation](#problem-formulation)
  - [Algorithms Implemented](#algorithms-implemented)
  - [Outputs & Visualizations](#outputs--visualizations)
  - [Interactive Web Visualizer](#interactive-web-visualizer)
  - [CLI Usage](#cli-usage)
- [Module 2: Maze with Keys & Doors (`maze/`)](#-module-2-maze-with-keys--doors-maze)
- [Module 3: Budget Traveller with Coupons (`budget_traveller_vs_code/`)](#-module-3-budget-traveller-with-coupons-budget_traveller_vs_code)
- [Module 4: Closest Pair of Points (`shortest/`)](#-module-4-closest-pair-of-points-shortest)
- [Repository Structure](#-repository-structure)
- [Quick Start Guide](#-quick-start-guide)
- [Tech Stack](#-tech-stack)

---

## 🧭 Overview of Challenges

| Challenge | Directory | Key DSA Techniques | Interface |
|---|---|---|---|
| **1. Exam Timetable Scheduling** | [`Scheduling/`](Scheduling/) | Capacitated Graph Colouring, Welsh-Powell, DSatur, Exact Branch & Bound | Modern Web App (Flask + Vis.js + Chart.js) & CLI |
| **2. Maze with Keys and Doors** | [`maze/`](maze/) | State Space Search, Bitmask BFS, Graph Theory | Java Swing Desktop GUI |
| **3. Budget Traveller with Coupons** | [`budget_traveller_vs_code/`](budget_traveller_vs_code/) | Modified Multi-State Dijkstra, Dynamic Programming | Streamlit Web Dashboard |
| **4. Closest Pair of Points** | [`shortest/`](shortest/) | Divide & Conquer ($O(N \log N)$), Recursion Tree Analysis | Matplotlib Animation & Charts |

---

## 🗓️ Module 1: Exam Timetable Scheduling (`Scheduling/`)

### Problem Formulation
A university has $N$ courses. Two courses conflict if at least one student is enrolled in both, meaning they cannot be scheduled in the same time slot. Additionally, each time slot has a strict hall capacity limit: at most $R$ exams can be held simultaneously.

The objective is to assign every course to a time slot such that:
1. **Conflict Constraint:** No two conflicting courses share the same slot.
2. **Capacity Constraint:** No time slot exceeds $R$ exams.
3. **Objective:** Minimize the total number of time slots used.

### Algorithms Implemented
1. **Greedy Heuristic 1 — Welsh-Powell:** Sorts courses by descending conflict degrees, greedily assigning the lowest feasible slot respecting conflicts and capacity $R$.
2. **Greedy Heuristic 2 — DSatur (Degree of Saturation):** Dynamically prioritizes vertices with the highest saturation degree (number of distinct slots used by neighbors), breaking ties with uncolored subgraph degrees.
3. **Exact Method — Branch & Bound Backtracking:**
   - **Theoretical Lower Bound:** $LB = \max(\lceil N / R \rceil, \omega(G))$, combining hall capacity and maximum clique size.
   - **Pruning 1 (Bound Pruning):** Backtracks if `current_slots >= best_slots`.
   - **Pruning 2 (Capacity Bound):** Backtracks if `current_slots + ceil(unassigned / R) >= best_slots`.
   - **Pruning 3 (Symmetry Breaking):** Evaluates at most one new empty slot to eliminate isomorphic permutations.
   - **Early Exit:** Terminates with proven optimality immediately upon matching the theoretical lower bound.

### Outputs & Visualizations
* **Output 1:** Minimum number of slots for each algorithm, execution runtime, and formal optimality proof.
* **Output 2:** Slot-wise course breakdown (e.g. `Slot 1: 2, 3, 9`).
* **Output 3:** Timetable export to [`timetable.csv`](Scheduling/timetable.csv) (rows = slots, columns = halls).
* **Visualizations:**
  * **Conflict Graph:** Force-directed network colored by assigned slot with legend.
  * **Timetable Grid:** Grid view with the **exact same color scheme** as the graph.
  * **Scalability Comparison:** Dual chart plotting slots used and runtime (log-scale) as $N$ increases.
  * **Assignment Animation:** Step-by-step animated GIF of the coloring process.

### Interactive Web Visualizer
The project includes a single-page web visualizer built with **Flask**, **Tailwind CSS**, **vis.js**, and **Chart.js**.

To run the web visualizer:
```bash
cd Scheduling
python3 app.py
```
Open **`http://127.0.0.1:5001`** in your browser.

**Web Visualizer Highlights:**
- **Option 1:** Text editor with sample presets (*Small University*, *Departmental Exams*, *Dense Challenge*) and `.txt` file uploader.
- **Option 2:** Interactive sliders for random graph generation ($N$, $R$, density $p$).
- **Interactive Network Graph:** Physics-based drag-and-drop, zoom, pan, and hover tooltips.
- **Step-by-Step Animation Player:** Play, pause, step forward/backward, and scrubbing slider with live decision explanations.
- **Dynamic Benchmarking:** Instant generation of scalability curves comparing all three algorithms.
- **CSV Export:** One-click download of the generated timetable.

### CLI Usage
Run directly from terminal without the web UI:
```bash
cd Scheduling

# Option 1: Run with an input file
python3 exam_scheduler.py --input-file sample_input.txt --animate

# Option 2: Run with random conflict graph (N=20 courses, R=4 per slot, density=0.30)
python3 exam_scheduler.py --generate 20 4 0.3 --animate
```

---

## 🗝️ Module 2: Maze with Keys & Doors (`maze/`)

A Java Swing application that generates and solves grid mazes containing keys (`a`-`f`) and matching locked doors (`A`-`F`).

### Key Features
- **Bitmask BFS:** State space search over $(row, col, \text{key\_mask})$ to compute the optimal path requiring key collection prior to door traversal.
- **Random Maze Generator:** Generates $N \times N$ mazes with 1–6 key/door pairs and guaranteed solvable corridors.
- **CSV Import/Export:** Import custom grid layouts and export solved trajectories as `solution.csv`.
- **Interactive GUI:** Real-time path animation, key inventory bar, door-unlock notifications, and color-coded pair highlights.

### Running the Maze Application
```bash
cd maze
javac Main.java
java Main
```

---

## ✈️ Module 3: Budget Traveller with Coupons (`budget_traveller_vs_code/`)

A Streamlit web application solving the constrained shortest path problem where a traveller has a limited number of discount coupons $K$ to apply on edge weights.

### Key Features
- **Multi-State Dijkstra:** Explores state tuples $(cost, node, coupons\_used)$ with priority queuing.
- **Interactive UI:** Dynamic graph topology input via CSV (`u, v, p`), source/destination picker, and coupon count controls.
- **Route Breakdown:** Step-by-step path breakdown showing which flights received coupon discounts.

### Running the Budget Traveller App
```bash
cd budget_traveller_vs_code
pip install -r requirements.txt
streamlit run app.py
```

---

## 📍 Module 4: Closest Pair of Points (`shortest/`)

A computational geometry implementation solving the 2D Closest Pair problem.

### Key Features
- **Divide & Conquer ($O(N \log N)$):** Presorts points by $X$ and $Y$ coordinates, recursively splits the plane, and inspects the central strip bounded by $\delta = \min(\delta_L, \delta_R)$ in linear time.
- **Brute Force Baseline ($O(N^2)$):** Benchmark comparator verifying correctness.
- **Visualizations:**
  - `closest_pair.png`: Scatter plot highlighting the closest pair and bounding box.
  - `recursion.gif`: Step-by-step animation of the recursive divide-and-conquer splitting.
  - `performance.png`: Empirical runtime comparison confirming theoretical time complexity.

### Running the Closest Pair Project
```bash
cd shortest/closest_pair_project
pip install -r requirements.txt
python closest_pair.py
```

---

## 📂 Repository Structure

```
DSA_Quadrax/
├── README.md                           # Main repository documentation
├── Scheduling/                         # Module 1: Exam Timetable Scheduling
│   ├── app.py                          # Flask REST API backend
│   ├── exam_scheduler.py               # Core coloring algorithms & CLI runner
│   ├── sample_input.txt                # Sample conflict graph
│   ├── timetable.csv                   # Exported exam timetable
│   ├── templates/                      # Tailwind HTML template
│   │   └── index.html
│   ├── static/                         # Frontend styles and controller
│   │   ├── css/style.css
│   │   └── js/main.js
│   └── outputs/                        # PNG charts and animated GIF
├── maze/                               # Module 2: Maze with Keys and Doors
│   ├── Main.java                       # Java Swing GUI & Bitmask BFS solver
│   └── README.txt                      # Maze module instructions
├── budget_traveller_vs_code/           # Module 3: Budget Traveller with Coupons
│   ├── app.py                          # Streamlit application
│   ├── requirements.txt                # Streamlit dependencies
│   └── README.md                       # Budget traveller documentation
└── shortest/                           # Module 4: Closest Pair of Points
    └── closest_pair_project/
        ├── closest_pair.py             # D&C implementation
        ├── requirements.txt            # Python dependencies
        └── README.md                   # Closest pair documentation
```

---

## ⚡ Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/nyx-suk/DSA_Quadrax.git
cd DSA_Quadrax
```

### 2. Environment Setup
Create and activate a Python virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate       # On macOS/Linux
# .venv\Scripts\activate        # On Windows
```

Install shared Python dependencies:
```bash
pip install flask networkx matplotlib pandas pillow streamlit
```

### 3. Launching Any Module
- **Exam Timetable Web App:** `cd Scheduling && python3 app.py` (open `http://127.0.0.1:5001`)
- **Maze GUI:** `cd maze && javac Main.java && java Main`
- **Budget Traveller:** `cd budget_traveller_vs_code && streamlit run app.py`
- **Closest Pair:** `cd shortest/closest_pair_project && python closest_pair.py`

---

## 🛠️ Tech Stack

- **Languages:** Python 3.10+, Java (JDK 8+)
- **Frameworks & Libraries:** Flask, Streamlit, NetworkX, NumPy, Pandas, Matplotlib, Pillow
- **Frontend & Web Visualizations:** HTML5 Canvas, Tailwind CSS, Vis.js (Network graph), Chart.js (Interactive benchmarks), Lucide Icons
- **Algorithms:** Graph Colouring (Welsh-Powell, DSatur), Branch & Bound with Symmetry Breaking, Bitmask BFS State Space Search, Multi-State Dijkstra, Divide & Conquer ($O(N \log N)$)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
