# Algorithm Lab — Closest Pair of Points

A visually styled comparative analysis of the **Brute Force** and **Divide and Conquer** closest-pair algorithms.

## Requirements
- Python 3.9+
- Matplotlib
- NumPy (listed as a project dependency; the algorithms themselves do not require it)

Install:
```bash
python -m pip install -r requirements.txt
```

## Run
```bash
python closest_pair.py
```
The program asks for `N`, generates random points, runs both algorithms, prints the closest pair and execution times, checks that both algorithms agree, and opens the visualizations.

Optional arguments:
```bash
python closest_pair.py --n 100
python closest_pair.py --n 100 --seed 7
python closest_pair.py --n 80 --animate
python closest_pair.py --n 1000 --no-benchmark
```

## What is included
- Brute-force closest pair: **O(N²)** time.
- Divide-and-conquer closest pair: **O(N log N)** time and **O(N)** auxiliary space.
- Dark, neon-accented point-field visualization with both algorithm pairs highlighted, the recursive divide line, and the strip region.
- Styled logarithmic running-time graph (`performance.png`).
- Optional step-through recursion animation (`--animate`).
- Printed coordinates, minimum distances, timing results, and an agreement check.
- Corner-case handling for `N < 2`, `N = 2`, duplicate points, collinear points, and equal x/y coordinates.

## Output files
- `closest_pair.png` — main visualization.
- `performance.png` — running-time comparison.

The displayed strip is a representative merge step from the recursive trace; the algorithm itself checks each recursive strip as part of the divide-and-conquer process.
