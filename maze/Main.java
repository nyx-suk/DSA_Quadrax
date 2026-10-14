import javax.swing.*;
import javax.swing.filechooser.FileNameExtensionFilter;
import java.awt.*;
import java.awt.event.*;
import java.awt.geom.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.List;

/**
 * VAULT RUNNER  -  Maze with Keys and Doors: playable game + BFS/A* solver + visualiser.
 * NOTE: the exit is always 'E', so a door 'E' cannot exist; pairs 5 and 6 use f/F and g/G.
 *
 * Run:   javac Main.java && java Main            (GUI)
 *        java Main 4                              (T = 4 key/door pairs)
 *        java Main 3 maze.csv                     (T hint + load CSV)
 *        echo 4 | java Main                       (T from standard input)
 *
 * Output 1 (integer shortest length or -1) is printed to stdout every time a maze is loaded/generated.
 * Output 2 (CSV with 'x' path) is produced by the "Export solution CSV" button.
 *
 * Core idea: BFS over the state (row, col, keyMask). Keys are never consumed, so the mask only grows;
 * the state space is N^2 * 2^T and each state is expanded once => O(N^2 * 2^T) time, same memory.
 */
public class Main extends JFrame {

    // ------------------------------------------------------------------ palette (one colour per key/door pair)
    static final Color[] PAL = {
            new Color(245, 180, 0),   // a/A gold
            new Color(33, 150, 243),  // b/B blue
            new Color(156, 39, 176),  // c/C purple
            new Color(236, 64, 122),  // d/D pink
            new Color(121, 85, 72),   // e (unused as a pair: door 'E' would clash with the exit)
            new Color(255, 111, 0),   // f/F orange
            new Color(0, 172, 193)    // g/G cyan (6th pair when T = 6, because 'E' is reserved for the exit)
    };
    static final Color GOOD = new Color(90, 225, 150), WARN = new Color(255, 120, 105), INFO = new Color(170, 184, 218);
    static final Color INK = new Color(60, 70, 90);   // dark text used on light banners

    static Color mix(Color a, Color b, double t) {
        t = Math.max(0, Math.min(1, t));
        return new Color((int) (a.getRed() + (b.getRed() - a.getRed()) * t),
                (int) (a.getGreen() + (b.getGreen() - a.getGreen()) * t),
                (int) (a.getBlue() + (b.getBlue() - a.getBlue()) * t));
    }
    static Color alpha(Color c, int a) { return new Color(c.getRed(), c.getGreen(), c.getBlue(), Math.max(0, Math.min(255, a))); }

    // ================================================================== SOLVER
    static final class Solver {
        static final int[] DR = {-1, 1, 0, 0}, DC = {0, 0, -1, 1};

        static final class Result {
            final List<int[]> path;   // cells from start to exit (inclusive) or null
            final int explored; final long nanos;
            Result(List<int[]> p, int e, long n) { path = p; explored = e; nanos = n; }
            int length() { return path == null ? -1 : path.size() - 1; }
        }

        /** Pair letters: a/A b/B c/C d/D f/F g/G  ('E' is the exit, so the 5th and 6th pairs skip it). T = number of bit slots. */
        static final int[] PAIR = {0, 1, 2, 3, 5, 6};
        static int slotsFor(int pairs) { return PAIR[pairs - 1] + 1; }
        static int keyBit(char ch, int T) { return (ch >= 'a' && ch < 'a' + T) ? 1 << (ch - 'a') : 0; }
        static int doorBit(char ch, int T) { return (ch >= 'A' && ch < 'A' + T && ch != 'E') ? 1 << (ch - 'A') : 0; }
        static int slotsOf(char[][] g) {
            int max = 0;
            for (char[] row : g) for (char ch : row) {
                if (ch >= 'a' && ch <= 'g') max = Math.max(max, ch - 'a' + 1);
                if (ch >= 'A' && ch <= 'G' && ch != 'E') max = Math.max(max, ch - 'A' + 1);
            }
            return Math.max(1, max);
        }

        /** BFS (astar=false) or A* with Manhattan heuristic (astar=true) over (cell, keyMask). Both are optimal. */
        static Result search(char[][] g, int T, int sr, int sc, int startMask, int er, int ec, boolean astar) {
            long t0 = System.nanoTime();
            int n = g.length, M = 1 << T;
            int[] dist = new int[n * n * M]; Arrays.fill(dist, -1);
            int[] par = new int[n * n * M];
            int sm = startMask | keyBit(g[sr][sc], T);
            int s = (sr * n + sc) * M + sm; dist[s] = 0; par[s] = -1;
            ArrayDeque<Integer> q = new ArrayDeque<>();
            PriorityQueue<int[]> pq = new PriorityQueue<>((x, y) -> Integer.compare(x[0], y[0]));
            if (astar) pq.add(new int[]{Math.abs(sr - er) + Math.abs(sc - ec), s}); else q.add(s);
            int explored = 0, goal = -1;
            while (astar ? !pq.isEmpty() : !q.isEmpty()) {
                int cur;
                if (astar) {
                    int[] e = pq.poll(); cur = e[1];
                    int cell = cur / M; int h = Math.abs(cell / n - er) + Math.abs(cell % n - ec);
                    if (e[0] != dist[cur] + h) continue;            // stale queue entry
                } else cur = q.poll();
                explored++;
                int mask = cur % M, cell = cur / M, r = cell / n, c = cell % n;
                if (r == er && c == ec) { goal = cur; break; }
                for (int d = 0; d < 4; d++) {
                    int nr = r + DR[d], nc = c + DC[d];
                    if (nr < 0 || nc < 0 || nr >= n || nc >= n) continue;
                    char ch = g[nr][nc];
                    if (ch == '#') continue;
                    int db = doorBit(ch, T);
                    if (db != 0 && (mask & db) == 0) continue;     // locked door
                    int nm = mask | keyBit(ch, T);                 // auto pick-up
                    int ni = (nr * n + nc) * M + nm, nd = dist[cur] + 1;
                    if (dist[ni] == -1 || (astar && nd < dist[ni])) {
                        dist[ni] = nd; par[ni] = cur;
                        if (astar) pq.add(new int[]{nd + Math.abs(nr - er) + Math.abs(nc - ec), ni}); else q.add(ni);
                    }
                }
            }
            List<int[]> path = null;
            if (goal != -1) {
                path = new ArrayList<>();
                for (int cur = goal; cur != -1; cur = par[cur]) { int cell = cur / M; path.add(new int[]{cell / n, cell % n}); }
                Collections.reverse(path);
            }
            return new Result(path, explored, System.nanoTime() - t0);
        }
    }

    // ================================================================== GENERATOR
    static final class Generator {
        /** Perfect maze (DFS backtracker) + a few loops; doors are placed on the S->E route, every key is placed
         *  in a region reachable BEFORE its door, so the maze is always solvable (verified by the solver). */
        static char[][] generate(int n, int T, double loops, Random rnd) {
            char[][] best = null; int bestScore = -1; final int slots = Solver.slotsFor(T);
            for (int attempt = 0; attempt < 14; attempt++) {
                char[][] g = carve(n, loops, rnd);
                int R = (n + 1) / 2, last = 2 * (R - 1);
                int sr = rnd.nextBoolean() ? last : 0, sc = rnd.nextBoolean() ? last : 0;
                int er = last - sr, ec = last - sc;
                List<int[]> route = route(g, sr, sc, er, ec);
                if (route == null) continue;
                int L = route.size() - 1;
                if (L < T + 2) continue;
                boolean[][] reserved = new boolean[n][n], onRoute = new boolean[n][n];
                reserved[sr][sc] = reserved[er][ec] = true;
                for (int[] p : route) onRoute[p[0]][p[1]] = true;
                int[][] door = new int[T][], key = new int[T][];
                int prev = 0;
                for (int i = 0; i < T; i++) {
                    int want = (int) Math.round((double) L * (i + 1) / (T + 1));
                    int lo = prev + 1, hi = L - 1 - (T - 1 - i);
                    int idx = Math.max(lo, Math.min(hi, want)); prev = idx;
                    door[i] = route.get(idx); reserved[door[i][0]][door[i][1]] = true;
                }
                boolean ok = true;
                for (int i = 0; i < T && ok; i++) {
                    boolean[][] blocked = new boolean[n][n];
                    for (int j = i; j < T; j++) blocked[door[j][0]][door[j][1]] = true;
                    int[][] dist = region(g, sr, sc, blocked);
                    List<int[]> off = new ArrayList<>(), any = new ArrayList<>();
                    for (int r = 0; r < n; r++) for (int c = 0; c < n; c++)
                        if (dist[r][c] > 0 && !reserved[r][c]) { any.add(new int[]{r, c}); if (!onRoute[r][c]) off.add(new int[]{r, c}); }
                    List<int[]> pool = off.isEmpty() ? any : off;
                    if (pool.isEmpty()) { ok = false; break; }
                    int[] pick = null;                       // farthest of 4 random picks => encourages detours
                    for (int t = 0; t < 4; t++) {
                        int[] cand = pool.get(rnd.nextInt(pool.size()));
                        if (pick == null || dist[cand[0]][cand[1]] > dist[pick[0]][pick[1]]) pick = cand;
                    }
                    key[i] = pick; reserved[pick[0]][pick[1]] = true;
                }
                if (!ok) continue;
                for (int i = 0; i < T; i++) { g[key[i][0]][key[i][1]] = (char) ('a' + Solver.PAIR[i]); g[door[i][0]][door[i][1]] = (char) ('A' + Solver.PAIR[i]); }
                g[sr][sc] = 'S'; g[er][ec] = 'E';
                Solver.Result res = Solver.search(g, slots, sr, sc, 0, er, ec, false);
                if (res.path == null) continue;
                int doorsUsed = 0;
                for (int[] p : res.path) if (Solver.doorBit(g[p[0]][p[1]], slots) != 0) doorsUsed++;
                int score = res.length() + 15 * doorsUsed;
                if (score > bestScore) { bestScore = score; best = g; }
            }
            return best != null ? best : snake(n, T, rnd);
        }

        static char[][] carve(int n, double loops, Random rnd) {
            char[][] g = new char[n][n];
            for (char[] row : g) Arrays.fill(row, '#');
            int R = (n + 1) / 2;
            boolean[][] vis = new boolean[R][R];
            ArrayDeque<int[]> st = new ArrayDeque<>();
            int r0 = rnd.nextInt(R), c0 = rnd.nextInt(R);
            vis[r0][c0] = true; g[2 * r0][2 * c0] = '.'; st.push(new int[]{r0, c0});
            int[] dr = {-1, 1, 0, 0}, dc = {0, 0, -1, 1};
            while (!st.isEmpty()) {
                int[] cur = st.peek();
                List<int[]> nb = new ArrayList<>();
                for (int d = 0; d < 4; d++) {
                    int nr = cur[0] + dr[d], nc = cur[1] + dc[d];
                    if (nr >= 0 && nc >= 0 && nr < R && nc < R && !vis[nr][nc]) nb.add(new int[]{nr, nc});
                }
                if (nb.isEmpty()) { st.pop(); continue; }
                int[] nx = nb.get(rnd.nextInt(nb.size()));
                vis[nx[0]][nx[1]] = true;
                g[cur[0] + nx[0]][cur[1] + nx[1]] = '.';     // wall between the two rooms
                g[2 * nx[0]][2 * nx[1]] = '.';
                st.push(nx);
            }
            List<int[]> walls = new ArrayList<>();
            for (int r = 0; r < 2 * R - 1; r++) for (int c = 0; c < 2 * R - 1; c++)
                if (((r + c) & 1) == 1 && g[r][c] == '#') walls.add(new int[]{r, c});
            Collections.shuffle(walls, rnd);
            int k = (int) (loops * R * R);
            for (int i = 0; i < k && i < walls.size(); i++) g[walls.get(i)[0]][walls.get(i)[1]] = '.';
            return g;
        }

        static List<int[]> route(char[][] g, int sr, int sc, int er, int ec) {
            int n = g.length; int[][] par = new int[n][n];
            for (int[] p : par) Arrays.fill(p, -2);
            ArrayDeque<int[]> q = new ArrayDeque<>(); q.add(new int[]{sr, sc}); par[sr][sc] = -1;
            while (!q.isEmpty()) {
                int[] cur = q.poll();
                if (cur[0] == er && cur[1] == ec) break;
                for (int d = 0; d < 4; d++) {
                    int nr = cur[0] + Solver.DR[d], nc = cur[1] + Solver.DC[d];
                    if (nr < 0 || nc < 0 || nr >= n || nc >= n || g[nr][nc] == '#' || par[nr][nc] != -2) continue;
                    par[nr][nc] = cur[0] * n + cur[1]; q.add(new int[]{nr, nc});
                }
            }
            if (par[er][ec] == -2) return null;
            List<int[]> out = new ArrayList<>();
            for (int cur = er * n + ec; cur != -1; cur = par[cur / n][cur % n]) out.add(new int[]{cur / n, cur % n});
            Collections.reverse(out); return out;
        }

        static int[][] region(char[][] g, int sr, int sc, boolean[][] blocked) {
            int n = g.length; int[][] dist = new int[n][n];
            for (int[] d : dist) Arrays.fill(d, -1);
            ArrayDeque<int[]> q = new ArrayDeque<>(); q.add(new int[]{sr, sc}); dist[sr][sc] = 0;
            while (!q.isEmpty()) {
                int[] cur = q.poll();
                for (int d = 0; d < 4; d++) {
                    int nr = cur[0] + Solver.DR[d], nc = cur[1] + Solver.DC[d];
                    if (nr < 0 || nc < 0 || nr >= n || nc >= n || g[nr][nc] == '#' || blocked[nr][nc] || dist[nr][nc] != -1) continue;
                    dist[nr][nc] = dist[cur[0]][cur[1]] + 1; q.add(new int[]{nr, nc});
                }
            }
            return dist;
        }

        /** Guaranteed fallback: boustrophedon corridor S, a, A, b, B, ..., E with random walls elsewhere. */
        static char[][] snake(int n, int T, Random rnd) {
            char[][] g = new char[n][n];
            for (char[] row : g) for (int c = 0; c < n; c++) row[c] = rnd.nextDouble() < 0.3 ? '#' : '.';
            for (int k = 0; k <= 2 * T + 1; k++) {
                int r = k / n, c = (r % 2 == 0) ? k % n : n - 1 - k % n;
                char ch = '.';
                if (k == 0) ch = 'S'; else if (k == 2 * T + 1) ch = 'E';
                else if (k % 2 == 1) ch = (char) ('a' + Solver.PAIR[(k - 1) / 2]); else ch = (char) ('A' + Solver.PAIR[(k - 2) / 2]);
                g[r][c] = ch;
            }
            return g;
        }
    }

    // ================================================================== CSV I/O
    static final class Loaded { char[][] g; int T; int pairs; String warning; }

    static Loaded parseCsv(Path p) throws IOException {
        List<String> lines = Files.readAllLines(p, StandardCharsets.UTF_8);
        List<char[]> rows = new ArrayList<>();
        for (String line : lines) {
            line = line.replace("\uFEFF", "").trim();
            if (line.isEmpty()) continue;
            String[] cells;
            if (line.contains(",")) cells = line.split(",", -1);
            else { cells = new String[line.length()]; for (int i = 0; i < cells.length; i++) cells[i] = String.valueOf(line.charAt(i)); }
            char[] row = new char[cells.length];
            for (int i = 0; i < cells.length; i++) {
                String s = cells[i].trim().replace("\"", "");
                if (s.length() != 1) throw new IOException("Row " + (rows.size() + 1) + ", column " + (i + 1) + ": each cell must be exactly one symbol (found \"" + s + "\").");
                row[i] = s.charAt(0);
            }
            rows.add(row);
        }
        if (rows.isEmpty()) throw new IOException("The file is empty.");
        int n = rows.size();
        if (n < 2) throw new IOException("The grid must be at least 2 x 2.");
        char[][] g = new char[n][n]; int s = 0, e = 0, maxIdx = -1;
        boolean[] hasKey = new boolean[7], hasDoor = new boolean[7];
        for (int r = 0; r < n; r++) {
            if (rows.get(r).length != n) throw new IOException("The grid must be square: row " + (r + 1) + " has " + rows.get(r).length + " cells but there are " + n + " rows.");
            for (int c = 0; c < n; c++) {
                char ch = rows.get(r)[c];
                if (ch == 'x') ch = '.';                       // allow re-loading an exported solution
                boolean key = ch >= 'a' && ch <= 'g', door = ch >= 'A' && ch <= 'G' && ch != 'E';   // 'E' is always the exit
                if (".#SE".indexOf(ch) < 0 && !key && !door) throw new IOException("Invalid symbol '" + ch + "' at row " + (r + 1) + ", column " + (c + 1) + ".");
                if (ch == 'S') s++; if (ch == 'E') e++;
                if (key) { hasKey[ch - 'a'] = true; maxIdx = Math.max(maxIdx, ch - 'a'); }
                if (door) { hasDoor[ch - 'A'] = true; maxIdx = Math.max(maxIdx, ch - 'A'); }
                g[r][c] = ch;
            }
        }
        if (s != 1) throw new IOException("The grid must contain exactly one 'S' (found " + s + ").");
        if (e != 1) throw new IOException("The grid must contain exactly one 'E' (found " + e + ").");
        Loaded L = new Loaded(); L.g = g; L.T = Math.max(1, maxIdx + 1);
        int pairs = 0; for (int k = 0; k < 7; k++) if (hasKey[k] || hasDoor[k]) pairs++; L.pairs = Math.max(1, pairs);
        StringBuilder w = new StringBuilder();
        for (int k = 0; k <= maxIdx; k++) {
            if (hasDoor[k] && !hasKey[k]) w.append("Door ").append((char) ('A' + k)).append(" has no key. ");
            if (hasKey[k] && !hasDoor[k]) w.append("Key ").append((char) ('a' + k)).append(k == 4 ? " has no door ('E' is the exit). " : " has no door. ");
        }
        L.warning = w.length() == 0 ? null : w.toString().trim();
        return L;
    }

    // ================================================================== PARTICLES
    static final class Particle { double x, y, vx, vy, size, life, age, rot, vr, grav; Color c; boolean rect; }

    // ================================================================== BOARD (game logic + rendering)
    static final class Board extends JPanel {
        interface Listener { void changed(); void message(String s, Color c); void tick(); }
        Listener listener;

        char[][] grid; int n, T, sr, sc, er, ec;
        int pr, pc, mask, openedMask;
        boolean[][] taken, opened, onSol; long[][] takenAt, openAt; long[] keyGotAt = new long[8]; boolean[] used = new boolean[8];
        final ArrayList<int[]> trail = new ArrayList<>();
        Solver.Result best, astar;
        boolean showSolution = false, won = false; long winAt;
        // movement tween
        boolean moving; int fr, fc, tr, tc, moveDur = 110; long moveStart; int bufDr, bufDc; boolean hasBuf;
        // feedback
        int shR = -1, shC = -1; long shAt;
        List<int[]> hint; long hintUntil;
        // auto-play
        List<int[]> auto; int autoIdx, autoDur = 230; boolean autoOn, paused;
        final List<Particle> parts = new ArrayList<>();
        final Random rnd = new Random();
        int cs = 20, ox, oy; long revealAt = System.currentTimeMillis();
        final javax.swing.Timer timer;

        Board() {
            setPreferredSize(new Dimension(720, 640)); setFocusable(true);
            timer = new javax.swing.Timer(16, e -> { tick(); repaint(); if (listener != null) listener.tick(); });
            timer.start();
            addMouseListener(new MouseAdapter() {
                @Override public void mousePressed(MouseEvent e) {
                    requestFocusInWindow();
                    if (grid == null) return;
                    int c = (e.getX() - ox) / cs, r = (e.getY() - oy) / cs;
                    if (e.getX() < ox || e.getY() < oy) return;
                    int dr = r - pr, dc = c - pc;
                    if (Math.abs(dr) + Math.abs(dc) == 1) tryMove(dr, dc);
                }
            });
            bind("UP", () -> tryMove(-1, 0)); bind("W", () -> tryMove(-1, 0));
            bind("DOWN", () -> tryMove(1, 0)); bind("S", () -> tryMove(1, 0));
            bind("LEFT", () -> tryMove(0, -1)); bind("A", () -> tryMove(0, -1));
            bind("RIGHT", () -> tryMove(0, 1)); bind("D", () -> tryMove(0, 1));
            bind("BACK_SPACE", this::undo); bind("Z", this::undo);
            bind("R", this::restart); bind("H", this::hint); bind("SPACE", this::togglePause); bind("P", this::toggleSolution);
        }

        private void bind(String key, Runnable r) {
            getInputMap(WHEN_IN_FOCUSED_WINDOW).put(KeyStroke.getKeyStroke(key), key);
            getActionMap().put(key, new AbstractAction() { public void actionPerformed(ActionEvent e) { r.run(); } });
        }
        void msg(String s, Color c) { if (listener != null) listener.message(s, c); }
        int steps() { return trail.size() - 1; }
        boolean isKey(char ch) { return ch >= 'a' && ch < 'a' + T; }
        boolean isDoor(char ch) { return ch >= 'A' && ch < 'A' + T && ch != 'E'; }

        // ---------------------------------------------------------------- loading / reset
        void load(char[][] g, int T) {
            this.grid = g; this.n = g.length; this.T = T;
            Arrays.fill(used, false);
            for (char[] row : g) for (char ch : row) {
                if (ch >= 'a' && ch <= 'g') used[ch - 'a'] = true;
                if (ch >= 'A' && ch <= 'G' && ch != 'E') used[ch - 'A'] = true;
            }
            for (int r = 0; r < n; r++) for (int c = 0; c < n; c++) {
                if (g[r][c] == 'S') { sr = r; sc = c; }
                if (g[r][c] == 'E') { er = r; ec = c; }
            }
            best = Solver.search(g, T, sr, sc, 0, er, ec, false);
            astar = Solver.search(g, T, sr, sc, 0, er, ec, true);
            onSol = new boolean[n][n];
            if (best.path != null) for (int[] p : best.path) onSol[p[0]][p[1]] = true;
            System.out.println(best.length());
            revealAt = System.currentTimeMillis();
            restart();
        }

        void restart() {
            if (grid == null) return;
            pr = sr; pc = sc; mask = 0; openedMask = 0;
            taken = new boolean[n][n]; opened = new boolean[n][n]; takenAt = new long[n][n]; openAt = new long[n][n];
            Arrays.fill(keyGotAt, 0);
            trail.clear(); trail.add(new int[]{sr, sc});
            moving = false; hasBuf = false; won = false; hint = null; autoOn = false; paused = false; shR = -1;
            parts.clear();
            msg("Reach the red exit. Arrow keys / WASD to move.", INFO);
            if (listener != null) listener.changed();
        }

        // ---------------------------------------------------------------- input / movement
        void tryMove(int dr, int dc) {
            if (grid == null || won) return;
            if (autoOn) { if (!paused) return; autoOn = false; }
            if (moving) { hasBuf = true; bufDr = dr; bufDc = dc; return; }
            int r = pr + dr, c = pc + dc; long now = System.currentTimeMillis();
            if (r < 0 || c < 0 || r >= n || c >= n) { shake(pr, pc, now); msg("That's the edge of the maze.", WARN); return; }
            char ch = grid[r][c];
            if (ch == '#') { shake(r, c, now); msg("A wall blocks the way.", WARN); return; }
            if (isDoor(ch) && (mask & (1 << (ch - 'A'))) == 0) {
                shake(r, c, now);
                msg("Door " + ch + " is locked - you need key '" + (char) (ch - 'A' + 'a') + "' first.", WARN); return;
            }
            begin(r, c, moveDur, now);
        }
        private void shake(int r, int c, long now) { shR = r; shC = c; shAt = now; }
        private void begin(int r, int c, int dur, long now) {
            moving = true; fr = pr; fc = pc; tr = r; tc = c; moveStart = now; moveDur = dur; hint = null;
        }

        void undo() {
            if (grid == null || moving || (autoOn && !paused)) return;
            autoOn = false; won = false; hasBuf = false;
            if (trail.size() <= 1) return;
            trail.remove(trail.size() - 1);
            mask = 0; openedMask = 0;
            taken = new boolean[n][n]; opened = new boolean[n][n];
            Arrays.fill(keyGotAt, 0);
            for (int[] p : trail) {
                char ch = grid[p[0]][p[1]];
                if (isKey(ch)) { taken[p[0]][p[1]] = true; takenAt[p[0]][p[1]] = 1; mask |= 1 << (ch - 'a'); keyGotAt[ch - 'a'] = 1; }
                if (isDoor(ch)) { opened[p[0]][p[1]] = true; openAt[p[0]][p[1]] = 1; openedMask |= 1 << (ch - 'A'); }
            }
            int[] last = trail.get(trail.size() - 1); pr = last[0]; pc = last[1]; hint = null;
            msg("Stepped back.", INFO);
            if (listener != null) listener.changed();
        }

        void hint() {
            if (grid == null || moving || won) return;
            Solver.Result r = Solver.search(grid, T, pr, pc, mask, er, ec, false);
            if (r.path == null) { msg("No route to the exit exists from here.", WARN); return; }
            hint = r.path; hintUntil = System.currentTimeMillis() + 4500;
            msg("Hint: the exit is " + r.length() + " step(s) away along the dashed route.", GOOD);
        }

        void toggleSolution() { showSolution = !showSolution; if (listener != null) listener.changed(); }

        void watchSolution() {
            if (grid == null) return;
            if (best.path == null) { msg("This maze has no solution (shortest path = -1).", WARN); return; }
            restart(); auto = best.path; autoIdx = 1; autoOn = true; paused = false; showSolution = true;
            msg("Watching the optimal solution (BFS)...", INFO);
            if (listener != null) listener.changed();
        }
        void togglePause() {
            if (autoOn) { paused = !paused; msg(paused ? "Paused. Space to resume, or move manually to take over." : "Resumed.", INFO); }
            else watchSolution();
        }
        void setSpeed(int level) { autoDur = 520 - level * 45; }   // level 1..10 => 475ms..70ms per step

        // ---------------------------------------------------------------- simulation
        void tick() {
            if (grid == null) return;
            long now = System.currentTimeMillis();
            for (Iterator<Particle> it = parts.iterator(); it.hasNext(); ) {
                Particle p = it.next(); double dt = 0.016;
                p.age += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += p.grav * dt; p.rot += p.vr * dt;
                if (p.age >= p.life) it.remove();
            }
            if (moving && rnd.nextInt(2) == 0) {                         // glowing comet tail behind the runner
                double t = Math.min(1, (now - moveStart) / (double) moveDur);
                Particle p = new Particle(); p.x = fc + (tc - fc) * t + .5 + rnd.nextGaussian() * .05; p.y = fr + (tr - fr) * t + .5 + rnd.nextGaussian() * .05;
                p.vx = rnd.nextGaussian() * .25; p.vy = rnd.nextGaussian() * .25; p.size = .08 + rnd.nextDouble() * .07; p.life = .38; p.c = new Color(179, 136, 255);
                parts.add(p);
            }
            if (moving && now - moveStart >= moveDur) arrive(now);
            if (!moving && !won) {
                if (hasBuf) { hasBuf = false; tryMove(bufDr, bufDc); }
                else if (autoOn && !paused) {
                    if (autoIdx < auto.size()) { int[] nx = auto.get(autoIdx++); begin(nx[0], nx[1], autoDur, now); }
                    else autoOn = false;
                }
            }
        }

        private void arrive(long now) {
            moving = false; pr = tr; pc = tc; trail.add(new int[]{pr, pc});
            char ch = grid[pr][pc];
            if (isKey(ch) && !taken[pr][pc]) {
                int k = ch - 'a'; taken[pr][pc] = true; takenAt[pr][pc] = now;
                if ((mask & (1 << k)) == 0) keyGotAt[k] = now;
                mask |= 1 << k; burst(pc + .5, pr + .5, PAL[k], 28);
                msg("Picked up key '" + ch + "' - door " + (char) (ch - 'a' + 'A') + " can now be opened.", GOOD);
            } else if (isDoor(ch) && !opened[pr][pc]) {
                int k = ch - 'A'; opened[pr][pc] = true; openAt[pr][pc] = now; openedMask |= 1 << k;
                burst(pc + .5, pr + .5, PAL[k], 32);
                msg("Door " + ch + " unlocked!", GOOD);
            } else if (pr == er && pc == ec) {
                won = true; winAt = now; autoOn = false;
                for (int i = 0; i < 160; i++) {
                    Particle p = new Particle(); p.x = rnd.nextDouble() * n; p.y = -1 - rnd.nextDouble() * 3;
                    p.vx = rnd.nextGaussian() * 0.8; p.vy = 2 + rnd.nextDouble() * 3; p.grav = 1.5; p.size = 0.12 + rnd.nextDouble() * 0.12;
                    p.life = 3.5 + rnd.nextDouble() * 1.5; p.c = PAL[rnd.nextInt(7)]; p.rect = true; p.vr = rnd.nextGaussian() * 6;
                    parts.add(p);
                }
                int par = best.length();
                msg("You escaped in " + steps() + " steps" + (par >= 0 ? " (optimal: " + par + ")." : "."), GOOD);
            }
            if (listener != null) listener.changed();
        }

        private void burst(double x, double y, Color c, int count) {
            for (int i = 0; i < count; i++) {
                Particle p = new Particle(); double a = rnd.nextDouble() * Math.PI * 2, sp = 1.5 + rnd.nextDouble() * 3;
                p.x = x; p.y = y; p.vx = Math.cos(a) * sp; p.vy = Math.sin(a) * sp; p.grav = 3;
                p.size = 0.05 + rnd.nextDouble() * 0.06; p.life = 0.5 + rnd.nextDouble() * 0.5; p.c = c; parts.add(p);
            }
        }

        // ---------------------------------------------------------------- icons
        static void keyIcon(Graphics2D g, double cx, double cy, double s, Color col) {
            AffineTransform old = g.getTransform();
            g.translate(cx, cy); g.rotate(-Math.PI / 4);
            g.setColor(col); g.setStroke(new BasicStroke((float) Math.max(1.5, s * 0.11), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            double hr = s * 0.17;
            g.draw(new Ellipse2D.Double(-s * 0.4 - hr, -hr, 2 * hr, 2 * hr));
            g.draw(new Line2D.Double(-s * 0.4 + hr, 0, s * 0.38, 0));
            g.draw(new Line2D.Double(s * 0.38, 0, s * 0.38, s * 0.17));
            g.draw(new Line2D.Double(s * 0.22, 0, s * 0.22, s * 0.13));
            g.setTransform(old);
        }
        /** open = 0 closed padlock ... 1 fully unlocked padlock (shackle lifted). */
        static void lockIcon(Graphics2D g, double cx, double cy, double s, Color col, double open) {
            double bw = s * 0.5, bh = s * 0.36, bx = cx - bw / 2, by = cy - bh / 2 + s * 0.12;
            double sw = bw * 0.62, lift = open * s * 0.13, cy0 = by - s * 0.1 - lift;
            g.setColor(col); g.setStroke(new BasicStroke((float) Math.max(1.5, s * 0.09), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
            g.draw(new Arc2D.Double(cx - sw / 2, cy0 - sw / 2, sw, sw, 0, 180, Arc2D.OPEN));
            g.draw(new Line2D.Double(cx - sw / 2, cy0, cx - sw / 2, by));
            g.draw(new Line2D.Double(cx + sw / 2, cy0, cx + sw / 2, cy0 + (by - cy0) * (1 - open * 0.7)));
            g.fill(new RoundRectangle2D.Double(bx, by, bw, bh, s * 0.1, s * 0.1));
            g.setColor(alpha(Color.WHITE, 230));
            g.fill(new Ellipse2D.Double(cx - s * 0.04, by + bh * 0.28, s * 0.08, s * 0.08));
            g.fill(new Rectangle2D.Double(cx - s * 0.015, by + bh * 0.4, s * 0.03, bh * 0.3));
        }
        static void text(Graphics2D g, String t, double cx, double cy, float size, Color c) {
            g.setFont(new Font(Font.SANS_SERIF, Font.BOLD, Math.round(size))); g.setColor(c);
            FontMetrics fm = g.getFontMetrics();
            g.drawString(t, (float) (cx - fm.stringWidth(t) / 2.0), (float) (cy + (fm.getAscent() - fm.getDescent()) / 2.0));
        }

        // ---------------------------------------------------------------- painting
        @Override protected void paintComponent(Graphics g0) {
            super.paintComponent(g0);
            Graphics2D g2 = (Graphics2D) g0.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            g2.setRenderingHint(RenderingHints.KEY_STROKE_CONTROL, RenderingHints.VALUE_STROKE_PURE);
            g2.setPaint(new GradientPaint(0, 0, new Color(12, 16, 34), 0, getHeight(), new Color(30, 22, 62)));
            g2.fillRect(0, 0, getWidth(), getHeight());
            if (grid == null) { g2.dispose(); return; }
            long now = System.currentTimeMillis();
            int pad = 16;
            cs = Math.max(8, Math.min((getWidth() - 2 * pad) / n, (getHeight() - 2 * pad) / n));
            ox = (getWidth() - cs * n) / 2; oy = (getHeight() - cs * n) / 2;
            for (int gl = 6; gl >= 1; gl--) { g2.setColor(new Color(0, 229, 255, 14 + (6 - gl) * 6)); g2.fillRoundRect(ox - gl * 2, oy - gl * 2, cs * n + gl * 4, cs * n + gl * 4, 14, 14); }
            boolean[][] vis = new boolean[n][n];
            for (int[] p : trail) vis[p[0]][p[1]] = true;
            Shape oldClip = g2.getClip();
            g2.clip(new RoundRectangle2D.Double(ox, oy, cs * n, cs * n, 10, 10));
            for (int r = 0; r < n; r++) for (int c = 0; c < n; c++) {          // diagonal "vault unlocking" reveal
                double rv = Math.min(1, (now - revealAt - (r + c) * 18L) / 320.0);
                if (rv <= 0) continue;
                Composite oc = g2.getComposite();
                if (rv < 1) g2.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, (float) rv));
                drawCell(g2, r, c, now, vis[r][c]);
                g2.setComposite(oc);
            }
            g2.setClip(oldClip);

            // player position (interpolated, eased)
            double px = pc + .5, py = pr + .5;
            if (moving) {
                double t = Math.min(1, (now - moveStart) / (double) moveDur); t = t * t * (3 - 2 * t);
                px = fc + (tc - fc) * t + .5; py = fr + (tr - fr) * t + .5;
            }
            // optimal-solution ghost path
            if (showSolution && best != null && best.path != null)
                polyline(g2, best.path, null, new Color(255, 143, 0, 200), cs * 0.13f, true);
            // path taken
            polyline(g2, trail, new double[]{px, py}, new Color(0, 150, 136, 190), cs * 0.2f, false);
            // hint route
            if (hint != null && now < hintUntil) {
                double f = Math.min(1, (hintUntil - now) / 800.0);
                polyline(g2, hint, null, new Color(233, 30, 99, (int) (230 * f)), cs * 0.16f, true);
            }
            // player
            double pulse = 0.5 + 0.5 * Math.sin(now / 220.0);
            double cx = ox + px * cs, cy = oy + py * cs;
            g2.setColor(new Color(103, 58, 183, (int) (45 + 35 * pulse)));
            g2.fill(new Ellipse2D.Double(cx - cs * 0.55, cy - cs * 0.55, cs * 1.1, cs * 1.1));
            g2.setPaint(new RadialGradientPaint((float) (cx - cs * 0.08), (float) (cy - cs * 0.1), (float) (cs * 0.34),
                    new float[]{0f, 1f}, new Color[]{new Color(179, 136, 255), new Color(81, 45, 168)}));
            g2.fill(new Ellipse2D.Double(cx - cs * 0.3, cy - cs * 0.3, cs * 0.6, cs * 0.6));
            g2.setColor(Color.WHITE); g2.setStroke(new BasicStroke(Math.max(1.5f, cs / 14f)));
            g2.draw(new Ellipse2D.Double(cx - cs * 0.3, cy - cs * 0.3, cs * 0.6, cs * 0.6));
            int held = 0;
            for (int k = 0; k < T; k++) if ((mask & (1 << k)) != 0) {
                double dx = cx + (held - (Integer.bitCount(mask) - 1) / 2.0) * cs * 0.17;
                g2.setColor(PAL[k]); g2.fill(new Ellipse2D.Double(dx - cs * 0.06, cy + cs * 0.3, cs * 0.12, cs * 0.12)); held++;
            }
            // particles
            for (Particle p : parts) {
                double a = 1 - p.age / p.life; g2.setColor(alpha(p.c, (int) (255 * Math.max(0, a))));
                double x = ox + p.x * cs, y = oy + p.y * cs, sz = p.size * cs;
                if (p.rect) {
                    AffineTransform old = g2.getTransform(); g2.rotate(p.rot, x, y);
                    g2.fill(new Rectangle2D.Double(x - sz / 2, y - sz / 4, sz, sz / 2)); g2.setTransform(old);
                } else g2.fill(new Ellipse2D.Double(x - sz / 2, y - sz / 2, sz, sz));
            }
            // auto-play badge
            if (autoOn) {
                g2.setColor(new Color(30, 40, 70, 200)); g2.fillRoundRect(ox + 8, oy + 8, 120, 26, 14, 14);
                text(g2, paused ? "PAUSED" : "AUTO-PLAY", ox + 68, oy + 21, 12f, Color.WHITE);
            }
            // victory banner
            if (won) {
                double f = Math.max(0, Math.min(1, (now - winAt) / 400.0));
                int w = Math.min(getWidth() - 40, 420), h = 130, bx = (getWidth() - w) / 2, by = (getHeight() - h) / 2;
                g2.setColor(new Color(255, 255, 255, (int) (235 * f))); g2.fillRoundRect(bx, by, w, h, 26, 26);
                g2.setColor(alpha(new Color(0, 150, 136), (int) (255 * f))); g2.setStroke(new BasicStroke(3f)); g2.drawRoundRect(bx, by, w, h, 26, 26);
                int par = best.length();
                text(g2, steps() == par ? "PERFECT ESCAPE!" : "YOU ESCAPED!", getWidth() / 2.0, by + 38, 28f, alpha(new Color(0, 121, 107), (int) (255 * f)));
                text(g2, "Your steps: " + steps() + "     Optimal: " + par, getWidth() / 2.0, by + 74, 16f, alpha(INK, (int) (255 * f)));
                text(g2, "R = restart   Z = undo   Space = watch solution", getWidth() / 2.0, by + 104, 12f, alpha(INK, (int) (200 * f)));
            }
            g2.dispose();
        }

        private void polyline(Graphics2D g2, List<int[]> pts, double[] tail, Color col, float w, boolean dashed) {
            if (pts.size() < 1) return;
            Path2D.Double path = new Path2D.Double();
            boolean first = true;
            for (int[] p : pts) {
                double x = ox + (p[1] + .5) * cs, y = oy + (p[0] + .5) * cs;
                if (first) { path.moveTo(x, y); first = false; } else path.lineTo(x, y);
            }
            if (tail != null) path.lineTo(ox + tail[0] * cs, oy + tail[1] * cs);
            float[] dash = dashed ? new float[]{cs * 0.3f, cs * 0.22f} : null;
            g2.setStroke(new BasicStroke(w, BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND, 10f, dash, 0f));
            g2.setColor(col); g2.draw(path);
        }

        private void drawCell(Graphics2D g2, int r, int c, long now, boolean vis) {
            double x = ox + c * cs, y = oy + r * cs; int s = cs;
            if (r == shR && c == shC) { double age = now - shAt; if (age < 400) x += Math.sin(age / 16.0) * (1 - age / 400.0) * s * 0.14; }
            char ch = grid[r][c];
            if (ch == '#') {
                g2.setColor(new Color(26, 28, 36)); g2.fill(new Rectangle2D.Double(x, y, s, s));
                g2.setColor(new Color(46, 50, 64)); g2.fill(new Rectangle2D.Double(x + s * .12, y + s * .12, s * .76, s * .76));
                if (s >= 14) {                                              // brick mortar lines
                    boolean ev = ((r + c) & 1) == 0;
                    g2.setColor(new Color(26, 28, 36)); g2.setStroke(new BasicStroke(1f));
                    g2.draw(new Line2D.Double(x + s * .12, y + s * .5, x + s * .88, y + s * .5));
                    g2.draw(new Line2D.Double(x + s * (ev ? .4 : .6), y + s * .12, x + s * (ev ? .4 : .6), y + s * .5));
                    g2.draw(new Line2D.Double(x + s * (ev ? .6 : .4), y + s * .5, x + s * (ev ? .6 : .4), y + s * .88));
                }
                return;
            }
            g2.setColor(Color.WHITE); g2.fill(new Rectangle2D.Double(x, y, s, s));
            if (showSolution && onSol[r][c]) { g2.setColor(new Color(255, 236, 200)); g2.fill(new Rectangle2D.Double(x, y, s, s)); }
            if (vis) { g2.setColor(new Color(204, 244, 232)); g2.fill(new Rectangle2D.Double(x, y, s, s)); }
            g2.setColor(new Color(221, 226, 234)); g2.setStroke(new BasicStroke(1f)); g2.draw(new Rectangle2D.Double(x, y, s, s));
            double cx = x + s / 2.0, cy = y + s / 2.0;
            if (ch == 'S') {
                g2.setPaint(new GradientPaint((float) x, (float) y, new Color(88, 214, 123), (float) x, (float) (y + s), new Color(39, 160, 78)));
                g2.fill(new RoundRectangle2D.Double(x + 2, y + 2, s - 4, s - 4, s * .3, s * .3));
                if (s >= 14) text(g2, "S", cx, cy, Math.max(10, s * .5f), Color.WHITE);
            } else if (ch == 'E') {
                double pl = 0.5 + 0.5 * Math.sin(now / 260.0);
                g2.setColor(new Color(229, 57, 53, (int) (50 + 70 * pl)));
                g2.fill(new Ellipse2D.Double(cx - s * (.5 + .1 * pl), cy - s * (.5 + .1 * pl), s * (1 + .2 * pl), s * (1 + .2 * pl)));
                g2.setPaint(new GradientPaint((float) x, (float) y, new Color(255, 112, 100), (float) x, (float) (y + s), new Color(211, 47, 47)));
                g2.fill(new RoundRectangle2D.Double(x + 2, y + 2, s - 4, s - 4, s * .3, s * .3));
                g2.setColor(new Color(255, 255, 255, 210)); g2.setStroke(new BasicStroke(Math.max(1.5f, s / 15f), BasicStroke.CAP_ROUND, BasicStroke.JOIN_ROUND));
                double rr = s * 0.4, ang = now / 5.0;
                g2.draw(new Arc2D.Double(cx - rr, cy - rr, 2 * rr, 2 * rr, ang, 75, Arc2D.OPEN));
                g2.draw(new Arc2D.Double(cx - rr, cy - rr, 2 * rr, 2 * rr, ang + 180, 75, Arc2D.OPEN));
                if (s >= 14) text(g2, "E", cx, cy, Math.max(10, s * .45f), Color.WHITE);
            } else if (isKey(ch)) {
                int k = ch - 'a'; double p = 0;
                if (taken[r][c]) p = takenAt[r][c] == 1 ? 1 : Math.min(1, (now - takenAt[r][c]) / 450.0);
                if (p < 1) {
                    double bob = Math.sin(now / 300.0 + r * 1.7 + c) * s * 0.04;
                    double sc2 = 1 - p * 0.6, rise = p * s * 0.45;
                    g2.setColor(alpha(PAL[k], (int) (45 * (1 - p)))); g2.fill(new Ellipse2D.Double(cx - s * .38, cy - s * .38, s * .76, s * .76));
                    Composite oc = g2.getComposite();
                    g2.setComposite(AlphaComposite.getInstance(AlphaComposite.SRC_OVER, (float) (1 - p)));
                    keyIcon(g2, cx, cy + bob - rise, s * .8 * sc2, PAL[k]);
                    g2.setComposite(oc);
                }
            } else if (isDoor(ch)) {
                int k = ch - 'A'; boolean open = opened[r][c];
                double p = open ? (openAt[r][c] == 1 ? 1 : Math.min(1, (now - openAt[r][c]) / 500.0)) : 0;
                Color fill = mix(PAL[k], Color.WHITE, p);
                g2.setColor(fill); g2.fill(new RoundRectangle2D.Double(x + 2, y + 2, s - 4, s - 4, s * .2, s * .2));
                if (!open && (mask & (1 << k)) != 0) {                      // you hold the key: pulse "can open"
                    double pl = 0.5 + 0.5 * Math.sin(now / 180.0);
                    g2.setColor(new Color(255, 255, 255, (int) (120 + 120 * pl))); g2.setStroke(new BasicStroke(Math.max(2f, s / 9f)));
                    g2.draw(new RoundRectangle2D.Double(x + 3, y + 3, s - 6, s - 6, s * .2, s * .2));
                }
                g2.setColor(PAL[k]); g2.setStroke(new BasicStroke(Math.max(1.5f, s / 14f)));
                g2.draw(new RoundRectangle2D.Double(x + 2, y + 2, s - 4, s - 4, s * .2, s * .2));
                if (r == shR && c == shC && now - shAt < 400) {
                    g2.setColor(new Color(229, 57, 53, (int) (150 * (1 - (now - shAt) / 400.0)))); g2.fill(new RoundRectangle2D.Double(x + 2, y + 2, s - 4, s - 4, s * .2, s * .2));
                }
                if (open && p < 1) {                                          // unlock shock-ring
                    g2.setColor(alpha(PAL[k], (int) (200 * (1 - p)))); g2.setStroke(new BasicStroke(Math.max(2f, s / 10f)));
                    double rr = s * (0.3 + 0.7 * p); g2.draw(new Ellipse2D.Double(cx - rr, cy - rr, 2 * rr, 2 * rr));
                }
                Color lc = mix(Color.WHITE, mix(PAL[k], Color.BLACK, 0.1), p);
                lockIcon(g2, cx, cy, s * .78, lc, p);
                if (s >= 26) text(g2, String.valueOf(ch), x + s * .17, y + s * .17, Math.max(8, s * .22f), lc);
            }
        }
    }

    // ================================================================== INVENTORY PANEL
    static final class Inventory extends JPanel {
        final Board b;
        Inventory(Board b) { this.b = b; setPreferredSize(new Dimension(270, 96)); setMaximumSize(new Dimension(Integer.MAX_VALUE, 96)); setOpaque(false); }
        @Override protected void paintComponent(Graphics g0) {
            Graphics2D g = (Graphics2D) g0.create();
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            List<Integer> ks = new ArrayList<>();
            for (int k = 0; k < b.T; k++) if (b.used[k]) ks.add(k);
            int cnt = Math.max(1, ks.size()); int slot = cnt > 6 ? 34 : 40, gap = 4; long now = System.currentTimeMillis();
            int total = cnt * slot + (cnt - 1) * gap, x0 = (getWidth() - total) / 2;
            for (int i = 0; i < ks.size(); i++) {
                int k = ks.get(i);
                int x = x0 + i * (slot + gap), y = 4;
                boolean has = (b.mask & (1 << k)) != 0, open = (b.openedMask & (1 << k)) != 0;
                g.setColor(has ? alpha(PAL[k], 60) : new Color(30, 37, 66)); g.fillRoundRect(x, y, slot, slot, 12, 12);
                g.setColor(has ? PAL[k] : new Color(70, 80, 118)); g.setStroke(new BasicStroke(2f)); g.drawRoundRect(x, y, slot, slot, 12, 12);
                double pop = 1;
                if (b.keyGotAt[k] > 1) { double t = (now - b.keyGotAt[k]) / 500.0; if (t < 1) pop = 1 + 0.45 * Math.sin(t * Math.PI); }
                Board.keyIcon(g, x + slot / 2.0, y + slot / 2.0, slot * 0.78 * pop, has ? PAL[k] : new Color(85, 96, 135));
                Board.lockIcon(g, x + slot / 2.0, y + slot + 22, 28, open ? PAL[k] : new Color(85, 96, 135), open ? 1 : 0);
            }
            g.dispose();
        }
    }

    // ================================================================== LEGEND
    static final class Legend extends JPanel {
        Legend() { setPreferredSize(new Dimension(270, 78)); setMaximumSize(new Dimension(Integer.MAX_VALUE, 78)); setOpaque(false); setAlignmentX(Component.LEFT_ALIGNMENT); }
        @Override protected void paintComponent(Graphics g0) {
            Graphics2D g = (Graphics2D) g0.create();
            g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            Color[] cols = {Color.WHITE, Color.BLACK, new Color(46, 170, 85), new Color(229, 57, 53)};
            String[] names = {"Open", "Wall", "Start", "Exit"};
            g.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 11));
            for (int i = 0; i < 4; i++) {
                int x = 2 + i * 66;
                g.setColor(cols[i]); g.fillRoundRect(x, 4, 16, 16, 5, 5);
                g.setColor(new Color(120, 132, 175)); g.drawRoundRect(x, 4, 16, 16, 5, 5);
                g.setColor(new Color(215, 222, 245)); g.drawString(names[i], x + 21, 16);
            }
            for (int k = 0; k < 6; k++) {
                int idx = Solver.PAIR[k], x = 2 + k * 44;
                g.setColor(PAL[idx]); g.fillRoundRect(x, 32, 38, 18, 6, 6);
                g.setColor(Color.WHITE); g.setFont(new Font(Font.MONOSPACED, Font.BOLD, 12));
                g.drawString((char) ('a' + idx) + "/" + (char) ('A' + idx), x + 5, 45);
            }
            g.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 10)); g.setColor(new Color(140, 152, 190));
            g.drawString("Each key opens only its same-coloured door.", 2, 66);
            g.dispose();
        }
    }

    // ================================================================== MAIN WINDOW
    private final Board board = new Board();
    private final Inventory inventory = new Inventory(board);
    private final JLabel statusLabel = new JLabel(" ");
    private final JLabel stepsLabel = new JLabel(), parLabel = new JLabel(), solverLabel = new JLabel();
    private final JLabel sizeLabel = new JLabel(), keysLabel = new JLabel(), loopLabel = new JLabel();
    private final JSlider sizeSlider = new JSlider(4, 40, 13), keySlider = new JSlider(1, 6, 3),
            loopSlider = new JSlider(0, 25, 4), speedSlider = new JSlider(1, 10, 5);
    private final JToggleButton showPath = new JToggleButton("Show shortest path");
    private final Random rnd = new Random();

    public Main(int initialT, String csvPath) {
        super("VAULT RUNNER - keys, doors & the shortest escape");
        try { UIManager.setLookAndFeel(UIManager.getCrossPlatformLookAndFeelClassName()); } catch (Exception ignored) { }
        setDefaultCloseOperation(EXIT_ON_CLOSE);
        keySlider.setValue(Math.max(1, Math.min(6, initialT)));
        setLayout(new BorderLayout());
        add(board, BorderLayout.CENTER);

        JPanel side = new JPanel(); side.setLayout(new BoxLayout(side, BoxLayout.Y_AXIS));
        side.setBackground(new Color(16, 20, 38)); side.setBorder(BorderFactory.createEmptyBorder(14, 14, 14, 14));
        JLabel title = new JLabel("VAULT RUNNER"); title.setFont(new Font(Font.MONOSPACED, Font.BOLD, 27)); title.setForeground(new Color(0, 229, 255));
        side.add(left(title));
        side.add(left(small("Collect keys, open matching doors, reach the exit in the fewest steps. (Door letters skip E, the exit: a b c d f g.)")));
        side.add(vgap(8));

        side.add(section("MAZE"));
        side.add(sliderRow(sizeSlider, sizeLabel, v -> "Grid size: " + v + " x " + v));
        side.add(sliderRow(keySlider, keysLabel, v -> "Key / door pairs (T): " + v));
        side.add(sliderRow(loopSlider, loopLabel, v -> "Extra loops (easier): " + v + "%"));
        side.add(buttons(btn("New random maze", new Color(63, 81, 181), this::newMaze), btn("Open CSV...", new Color(96, 125, 139), this::openCsv)));

        side.add(section("PLAY"));
        side.add(buttons(btn("Undo (Z)", new Color(0, 137, 123), board::undo), btn("Restart (R)", new Color(0, 137, 123), board::restart),
                btn("Hint (H)", new Color(233, 30, 99), board::hint)));

        side.add(section("SOLVER"));
        showPath.setFocusable(false); showPath.setBackground(new Color(38, 46, 80)); showPath.setForeground(Color.WHITE); showPath.setOpaque(true); showPath.addActionListener(e -> { board.showSolution = showPath.isSelected(); board.repaint(); });
        side.add(left(showPath));
        side.add(buttons(btn("Watch solution (Space)", new Color(245, 124, 0), board::togglePause), btn("Export CSV", new Color(96, 125, 139), this::exportCsv)));
        JLabel spd = small("Animation speed"); side.add(left(spd));
        speedSlider.setFocusable(false); speedSlider.setOpaque(false); speedSlider.addChangeListener(e -> board.setSpeed(speedSlider.getValue()));
        board.setSpeed(speedSlider.getValue()); side.add(speedSlider);

        side.add(section("KEY INVENTORY"));
        side.add(inventory);

        side.add(section("LEGEND"));
        side.add(new Legend());
        side.add(section("STATS"));
        for (JLabel l : new JLabel[]{stepsLabel, parLabel, solverLabel}) { l.setFont(new Font(Font.MONOSPACED, Font.PLAIN, 12)); l.setForeground(new Color(225, 232, 250)); side.add(left(l)); }
        side.add(vgap(8));
        side.add(left(small("<html>Move: arrows / WASD or click an adjacent cell<br>Undo: Z / Backspace &nbsp; Hint: H &nbsp; Restart: R<br>Pause/watch: Space &nbsp; Path overlay: P</html>")));
        JScrollPane sp = new JScrollPane(side, ScrollPaneConstants.VERTICAL_SCROLLBAR_AS_NEEDED, ScrollPaneConstants.HORIZONTAL_SCROLLBAR_NEVER);
        sp.setBorder(BorderFactory.createMatteBorder(0, 2, 0, 0, new Color(0, 229, 255, 120))); sp.setPreferredSize(new Dimension(320, 640));
        sp.getVerticalScrollBar().setUnitIncrement(14);
        add(sp, BorderLayout.EAST);

        statusLabel.setBorder(BorderFactory.createEmptyBorder(8, 14, 8, 14)); statusLabel.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 13));
        statusLabel.setOpaque(true); statusLabel.setBackground(new Color(10, 13, 26));
        add(statusLabel, BorderLayout.SOUTH);

        board.listener = new Board.Listener() {
            public void changed() { refreshStats(); showPath.setSelected(board.showSolution); }
            public void message(String s, Color c) { statusLabel.setText(s); statusLabel.setForeground(c); }
            public void tick() { inventory.repaint(); }
        };
        setMinimumSize(new Dimension(940, 660));
        pack(); setLocationRelativeTo(null);

        boolean loaded = false;
        if (csvPath != null) loaded = loadCsv(Paths.get(csvPath));
        if (!loaded) newMaze();
        board.requestFocusInWindow();
    }

    private void refreshStats() {
        stepsLabel.setText("Your steps: " + board.steps());
        int par = board.best == null ? -1 : board.best.length();
        parLabel.setText("Shortest path (optimal): " + par);
        if (board.best != null) {
            long space = (long) board.n * board.n * (1L << board.T);
            solverLabel.setText(String.format("<html>BFS: %,d states, %.2f ms<br>A*: %,d states, %.2f ms<br>State space N&sup2;&middot;2^T = %,d</html>",
                    board.best.explored, board.best.nanos / 1e6, board.astar.explored, board.astar.nanos / 1e6, space));
        }
    }

    private void newMaze() {
        int T = keySlider.getValue(), n = sizeSlider.getValue();
        if (n < T + 6) { n = T + 6; sizeSlider.setValue(n); }         // room for T routes' worth of doors
        char[][] g = Generator.generate(n, T, loopSlider.getValue() / 100.0, rnd);
        board.showSolution = false; showPath.setSelected(false);
        board.load(g, Solver.slotsOf(g));
        board.msg("New " + n + " x " + n + " maze with " + T + " key/door pair(s). Good luck!", INFO);
        board.requestFocusInWindow();
    }

    private void openCsv() {
        JFileChooser ch = new JFileChooser(new File("."));
        ch.setFileFilter(new FileNameExtensionFilter("CSV files", "csv"));
        if (ch.showOpenDialog(this) == JFileChooser.APPROVE_OPTION) loadCsv(ch.getSelectedFile().toPath());
        board.requestFocusInWindow();
    }

    private boolean loadCsv(Path p) {
        try {
            Loaded L = parseCsv(p);
            sizeSlider.setValue(Math.max(4, Math.min(40, L.g.length))); keySlider.setValue(Math.min(6, L.pairs));
            board.showSolution = false; showPath.setSelected(false);
            board.load(L.g, L.T);
            int par = board.best.length();
            board.msg("Loaded " + p.getFileName() + " (" + L.g.length + " x " + L.g.length + "). Shortest path: " + par
                    + (L.warning != null ? "  |  Note: " + L.warning : ""), L.warning != null || par < 0 ? WARN : INFO);
            return true;
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, ex.getMessage(), "Could not load maze", JOptionPane.ERROR_MESSAGE);
            return false;
        }
    }

    private void exportCsv() {
        if (board.best == null || board.best.path == null) { JOptionPane.showMessageDialog(this, "This maze has no solution (-1) - nothing to export."); return; }
        JFileChooser ch = new JFileChooser(new File("."));
        ch.setSelectedFile(new File("solution.csv")); ch.setFileFilter(new FileNameExtensionFilter("CSV files", "csv"));
        if (ch.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;
        char[][] out = new char[board.n][];
        for (int r = 0; r < board.n; r++) out[r] = board.grid[r].clone();
        for (int[] p : board.best.path) if (out[p[0]][p[1]] == '.') out[p[0]][p[1]] = 'x';   // keys, doors, S, E stay identifiable
        StringBuilder sb = new StringBuilder();
        for (char[] row : out) { for (int c = 0; c < row.length; c++) { if (c > 0) sb.append(','); sb.append(row[c]); } sb.append('\n'); }
        try {
            Files.write(ch.getSelectedFile().toPath(), sb.toString().getBytes(StandardCharsets.UTF_8));
            board.msg("Solution exported to " + ch.getSelectedFile().getName() + " (length " + board.best.length() + ").", GOOD);
        } catch (IOException ex) { JOptionPane.showMessageDialog(this, "Could not save: " + ex.getMessage()); }
        board.requestFocusInWindow();
    }

    // ---------------------------------------------------------------- small UI helpers
    private interface Fmt { String f(int v); }
    private JPanel sliderRow(JSlider s, JLabel label, Fmt fmt) {
        s.setFocusable(false); s.setOpaque(false);
        label.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 12)); label.setForeground(new Color(215, 222, 245)); label.setText(fmt.f(s.getValue()));
        s.addChangeListener(e -> label.setText(fmt.f(s.getValue())));
        JPanel p = new JPanel(new BorderLayout()); p.setOpaque(false);
        p.add(label, BorderLayout.NORTH); p.add(s, BorderLayout.CENTER);
        p.setAlignmentX(Component.LEFT_ALIGNMENT); p.setMaximumSize(new Dimension(Integer.MAX_VALUE, 52)); return p;
    }
    private JButton btn(String text, Color bg, Runnable r) {
        JButton b = new JButton(text); b.setFocusable(false); b.setBackground(bg); b.setForeground(Color.WHITE);
        b.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 12)); b.setOpaque(true); b.setBorderPainted(false);
        b.setMargin(new Insets(7, 8, 7, 8)); b.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        b.addActionListener(e -> { r.run(); board.requestFocusInWindow(); }); return b;
    }
    private JPanel buttons(JButton... bs) {
        JPanel p = new JPanel(new GridLayout(1, bs.length, 6, 0)); p.setOpaque(false);
        for (JButton b : bs) p.add(b);
        p.setAlignmentX(Component.LEFT_ALIGNMENT); p.setMaximumSize(new Dimension(Integer.MAX_VALUE, 34)); return p;
    }
    private JLabel section(String t) {
        JLabel l = new JLabel(t); l.setFont(new Font(Font.SANS_SERIF, Font.BOLD, 11)); l.setForeground(new Color(0, 229, 255));
        l.setBorder(BorderFactory.createEmptyBorder(12, 0, 5, 0)); l.setAlignmentX(Component.LEFT_ALIGNMENT); return l;
    }
    private JLabel small(String t) { JLabel l = new JLabel(t); l.setFont(new Font(Font.SANS_SERIF, Font.PLAIN, 11)); l.setForeground(new Color(140, 152, 190)); return l; }
    private <C extends JComponent> C left(C c) { c.setAlignmentX(Component.LEFT_ALIGNMENT); return c; }
    private Component vgap(int h) { return Box.createVerticalStrut(h); }

    // ================================================================== ENTRY POINT
    public static void main(String[] args) {
        int t = 3; String csv = null;
        for (String a : args) { if (a.matches("\\d+")) t = Integer.parseInt(a); else csv = a; }
        try {   // "Standard input line: T": piped input is read; in a real terminal we prompt (never blocks the GUI otherwise)
            boolean given = false; for (String a : args) if (a.matches("\\d+")) given = true;
            if (!given && System.in.available() == 0 && System.console() != null) {
                System.out.print("Enter T (number of key/door types, 1-6): ");
                String line = System.console().readLine();
                if (line != null && line.trim().matches("\\d+")) t = Integer.parseInt(line.trim());
            } else if (!given && System.in.available() > 0) {
                String line = new BufferedReader(new InputStreamReader(System.in)).readLine();
                if (line != null && line.trim().matches("\\d+")) t = Integer.parseInt(line.trim());
            }
        } catch (IOException ignored) { }
        final int T = Math.max(1, Math.min(6, t)); final String file = csv;
        SwingUtilities.invokeLater(() -> new Main(T, file).setVisible(true));
    }
}
