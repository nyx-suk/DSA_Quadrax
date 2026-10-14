MAZE WITH KEYS AND DOORS — JAVA SWING

Requirements: Java JDK 8 or newer. No external libraries.

Run:
  javac Main.java
  java Main

Features:
- Random N x N maze generation with 1–6 key/door pairs and a guaranteed solvable corridor.
- Import square CSV grids (comma-separated cells or compact rows), using ., #, S, E, a-f, A-F.
- BFS shortest path with key inventory represented as a bitmask.
- Colour-coded grid, pair-specific colours, highlighted path, animated movement, key collection, inventory updates, and door-unlock marks.
- Export solution.csv; ordinary open path cells become x while S, E, keys, and doors remain identifiable.

CSV input example (5 x 5):
S,.,a,#,E
.,#,#,#,.
.,.,A,.,.
#,#,.,#,.
.,.,.,.,.

The number of key/door types is set in the UI. For a door to be traversable, its matching key must be collected first. Grid must be square and contain exactly one S and one E.
