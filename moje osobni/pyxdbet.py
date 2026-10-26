"""Bot for the BeatEvilTower stacking game.

Put the mouse on the stop button and press E while a row is moving. The bot
measures how fast the row is going, clicks at the moment it lines up with the
row below it, and then waits for E again.

    python pyxdbet.py              run the bot (the first run asks you to calibrate)
    python pyxdbet.py calibrate    calibrate again (after moving or resizing the game)
    python pyxdbet.py check        print what the bot sees right now

Keys:  E            play the moving row
       F8, F8       reselect the grid any time: F8 with the mouse on the middle of the
                    bottom-left cell, then F8 on the middle of the top-right cell
       numpad + / - click earlier / later by 5 ms
       Esc          quit
"""
import ctypes
import json
import os
import sys
import time
from collections import deque

import keyboard
import mss
import numpy as np

TRIGGER = "e"       # key that makes the bot play the row that's moving
COLS = 10           # columns in the grid
LIT_R, LIT_G, LIT_B = 110, 80, 225  # a pixel is part of a block if any color is above
                                    # these (the background stays below about 95/95/210)
FULL = 0.75         # a cell has a block if this much of its middle is lit (blocks fill all of
                    # it, text like the "2x" labels only about half)
LATENCY = 0.040     # the click delay (s) to aim with until enough clicks are known. After that
                    # the bot uses how the delay of the recent clicks was spread (it varies a lot)
PER_ROW = 60        # each row of the game learns from its own last this many clicks
SMOOTH = 0.003      # how much (s) the learned spread of delays is smoothed, so that a few
                    # clicks can't make it spiky and jumpy
START_WIDTH = 5     # blocks in the first row of a game (each row after it has one less, down to 1)
SIDE = 1            # while the tower narrows (rows 0-4), stack it against a side, this many
                    # columns in from the edge (1 = next to the outermost column), so all the
                    # 1-block rows stop there. None: anywhere on the row below
QUIET = 0.08        # after a click, take no screenshots for this long (s) so the PC is free to
                    # handle the click (heavy screen capturing can make the browser slower)
MIN_MOVES = 3       # moves to watch before trusting the measured speed
SAFETY = 0.002      # never plan a click closer than this to "now" (s)
STEP = 2            # look at every 2nd pixel row of the grid
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "pyxdbet_config.json")
LOG = os.path.join(HERE, "pyxdbet_log.txt")  # one line per click (also the delay history)

user32 = ctypes.windll.user32
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # real pixels, same as mss uses
except (AttributeError, OSError):
    user32.SetProcessDPIAware()


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def getcoords():
    p = POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def click():
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # left button down, wherever the mouse is
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # left button up


def waitfor(key):
    while not keyboard.is_pressed(key):
        time.sleep(0.02)
    while keyboard.is_pressed(key):
        time.sleep(0.02)


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_config(cfg):
    with open(CONFIG, "w") as f:
        json.dump(cfg, f, indent=2)


def make_config(bottom_left, top_right, old=None):
    """Grid settings from the middles of the bottom-left and top-right cells (None if
    the points don't make sense). Keeps the learned latency from the old settings."""
    (x0, y0), (x1, y1) = bottom_left, top_right
    pitch_x = (x1 - x0) / (COLS - 1)
    rows = round((y0 - y1) / pitch_x) + 1 if pitch_x > 0 else 0  # cells are square
    if pitch_x < 5 or rows < 2:
        return None
    old = old or {}
    return {"x0": x0, "y0": y0, "pitch_x": pitch_x, "pitch_y": (y0 - y1) / (rows - 1),
            "rows": rows, "latency": old.get("latency", LATENCY)}


def calibrate(old=None):
    print("Calibration: put the mouse on each spot and press F8.")
    spots = []
    for name in ("the MIDDLE of the bottom-left cell", "the MIDDLE of the top-right cell"):
        print("  ->", name)
        waitfor("f8")
        spots.append(getcoords())
        print("     ", spots[-1])
    cfg = make_config(*spots, old)
    if cfg is None:
        sys.exit("Those points don't look like the bottom-left and top-right cells, try again.")
    save_config(cfg)
    print(f"Grid: {COLS} columns x {cfg['rows']} rows, cells {cfg['pitch_x']:.1f}px. Saved to {CONFIG}")
    return cfg


class Grid:
    """Where the grid is on screen. It looks at every STEP-th pixel row ("line") and
    works out which columns have a block on it, so the rows can be anywhere
    (it doesn't matter how far the game scrolls)."""

    def __init__(self, cfg):
        px, self.py, self.rows = cfg["pitch_x"], cfg["pitch_y"], cfg["rows"]
        left = int(cfg["x0"] - px / 2)
        top = int(cfg["y0"] - (self.rows - 0.5) * self.py)
        self.box = {"left": left, "top": top,
                    "width": int(COLS * px) + 1, "height": int(self.rows * self.py) + 1}
        self.bottom = cfg["y0"] - top  # middle of the bottom row, inside the box
        h = max(2, int(px * 0.2))      # look at the middle 40% of each column
        self.n = 2 * h
        mids = [int(cfg["x0"] + c * px) - left for c in range(COLS)]
        self.xs = np.concatenate([np.arange(x - h, x + h) for x in mids])
        self.ys = np.arange(0, self.box["height"], STEP)

    def lines(self, img):
        """BGRA screenshot of self.box -> [line][column]: how much of the column's middle is lit."""
        px = img[np.ix_(self.ys, self.xs)]  # BGRA
        lit = (px[..., 2] > LIT_R) | (px[..., 1] > LIT_G) | (px[..., 0] > LIT_B)
        return lit.reshape(len(self.ys), COLS, self.n).mean(axis=2)

    def band(self, y):
        """The lines of the row whose middle is at y, or None if that's off the grid."""
        sel = np.abs(self.ys - y) <= 0.2 * self.py
        return sel if sel.sum() >= 0.15 * self.py / STEP else None


def cells(lines, band):
    """Which columns of a row have a block (filled, not just some text)."""
    return lines[band].mean(axis=0) > FULL


def span(row):
    """(first, last) column with a block if the row is one solid piece, else None."""
    idx = np.flatnonzero(row)
    if len(idx) == 0 or idx[-1] - idx[0] != len(idx) - 1:
        return None
    return int(idx[0]), int(idx[-1])


def ends(lines):
    """Per line: how many columns have a block, the first one, and if they're one solid piece."""
    count, first = lines.sum(axis=1), lines.argmax(axis=1)
    last = COLS - 1 - lines[:, ::-1].argmax(axis=1)
    return count, first, (count > 0) & (last - first + 1 == count)


class Bot:
    def __init__(self, grid, grab, press, latency=LATENCY, log=print):
        self.grid, self.grab, self.press, self.log = grid, grab, press, log
        self.armed = self.quit = False
        self.frame_time = 0.006  # how long one screenshot + analysis takes (measured)
        self.last_placed = None  # where our last row landed, in case it scrolls off the screen
        self.recent = None       # the last few seconds of screenshots, saved if something fails
        self.new_grid = None     # set when the grid is reselected (F8), used once the bot is free
        self.latency = latency   # used until enough clicks are known
        # For every row of the game (0 = the bottom one): its recent clicks, each as the time
        # range (s after the click) in which it took effect, which is the time the block was
        # on the spot where it stopped. The delay varies a lot from click to click, and some
        # rows are much slower than others (in the real game rows 5, 7, 9 and 11), so every
        # row learns its own spread of delays (see spread) and is clicked when that gives
        # the best chance (see best_click).
        self.delays = {}         # row -> [(start, end), ...]
        self.spreads = {}        # cache: row -> its spread of delays
        self.row_no = self.last_width = None  # the row clicked last and how wide it was
        self.nudge = 0.0         # manual adjustment from the + / - keys
        self.trace = deque(maxlen=150)  # (time, the moving row) for the click log

    def row_number(self, W, below):
        """Which row of the game this is (0 = the bottom one). A row with nothing below it,
        or wider than the last one, starts a new game (if it's narrower than START_WIDTH,
        the first rows were played without the bot)."""
        if below is None or self.last_width is None or W > self.last_width:
            return max(0, START_WIDTH - W)
        return self.row_no + 1

    def count(self, row, W):
        """Remember which row was clicked last."""
        self.row_no, self.last_width = row, W

    def load_history(self):
        """Get the delays of earlier clicks from the click log. Returns the step time (s) each
        row had the last time it was clicked."""
        speeds = {}
        try:
            with open(LOG) as f:
                lines = f.readlines()[-5000:]
        except OSError:
            return speeds
        for line in lines:
            try:
                r = json.loads(line)
                row = r.get("row")
                if row is None:  # logged before the rows were numbered
                    row = self.row_number(r["W"], r.get("below"))
                self.count(row, r["W"])
                speeds[row] = r["T"] / 1000
                j, w = r.get("j"), r.get("windows")
                if j is not None and w and 0 <= j < len(w) and not r.get("bounced"):
                    a, b = w[j][-2:]  # the widest range known for that spot
                    self.delays.setdefault(row, []).append((a / 1000, b / 1000))
            except (ValueError, KeyError, TypeError, IndexError):
                pass
        self.spreads = {}
        return speeds

    def spread(self, row):
        """How the click delay is spread on this row: (delays 1 ms apart, share of the clicks
        with that delay). From the row's own recent clicks; while it has fewer than 8, the
        clicks of the rows 2, 4, ... away from it (in the real game every other row is slow)
        together count for the missing ones. Each click took effect somewhere inside a known
        range: find the smooth spread that explains them all best."""
        if row not in self.spreads:
            grid = np.arange(-0.02, 0.15, 0.001)
            own, other = self.delays.get(row, [])[-PER_ROW:], []
            for r in sorted(self.delays, key=lambda r: ((r - row) % 2, abs(r - row))):
                if r != row and len(other) < 8:
                    other += self.delays[r][-PER_ROW:]
            weight = np.array([1.0] * len(own) + [max(0, 8 - len(own)) / max(1, len(other))] * len(other))
            inside = np.array([(grid >= a) & (grid < b) for a, b in own + other], float).reshape(-1, len(grid))
            keep = inside.any(axis=1) & (weight > 0)
            inside, weight = inside[keep], weight[keep]
            if len(own) + len(other) < 8 or not keep.any():
                p = np.zeros(len(grid))  # not enough clicks yet: use the latency from the settings
                p[np.abs(grid - self.latency).argmin()] = 1
            else:
                kernel = np.exp(-0.5 * (np.arange(-3 * SMOOTH, 3.01 * SMOOTH, 0.001) / SMOOTH) ** 2)
                p = np.full(len(grid), 1 / len(grid))
                for _ in range(150):
                    share = inside * p
                    p = weight @ (share / (share.sum(axis=1, keepdims=True) + 1e-12)) / weight.sum()
                    p = np.convolve(p, kernel / kernel.sum(), mode="same")
                p /= p.sum()
            self.spreads[row] = grid, p
        return self.spreads[row]

    def best_click(self, wins, spread, soonest, worth=None):
        """When to click (not before soonest) to stop the row on one of these spots, and the
        chance that works (or None if that's too soon). wins: for each spot (sure_start,
        sure_end, may_start, may_end, ...), see timing; worth: how much stopping on each
        spot counts (1 each if not given)."""
        grid, p = spread
        ts = np.arange(min(w[2] for w in wins) - 0.001, max(w[3] for w in wins) + 0.001, 0.001)
        on = np.zeros(len(ts))  # chance the row is on one of the spots, every 1 ms
        for (s0, s1, m0, m1, _), value in zip(wins, worth or [1.0] * len(wins)):
            arrived = np.clip((ts - m0) / max(s0 - m0, 1e-6), 0, 1)
            not_left = np.clip((m1 - ts) / max(m1 - s1, 1e-6), 0, 1)
            on += value * np.minimum(arrived, not_left)
        # chance[k]: how many of the delays would land a click at clicks[k] on a spot
        chance = np.convolve(np.minimum(on, 1), p[::-1])
        clicks = ts[0] - grid[-1] - self.nudge + 0.001 * np.arange(len(chance))
        good = np.flatnonzero(chance >= chance.max() - 0.01)
        runs = np.split(good, np.flatnonzero(np.diff(good) > 1) + 1)
        runs = [r for r in runs if clicks[r[len(r) // 2]] >= soonest]
        if not runs:
            return None
        run = max(runs, key=len)  # the middle of the longest stretch of (nearly) best ones
        k = run[len(run) // 2]
        return float(clicks[k]), float(chance[k])

    def lat(self, row, T):
        """(latency, chance) this row is clicked with, for a spot it is surely on for T s."""
        click, chance = self.best_click([(0.0, T, 0.0, T, None)], self.spread(row), -1.0)
        return T / 2 - click, chance

    def run(self):
        while not self.quit:
            if self.new_grid:
                self.grid, self.new_grid = self.new_grid, None
                self.last_placed = None  # it was measured on the old grid
            elif self.armed:
                self.armed = False
                self.play_row()
            else:
                time.sleep(0.005)

    def frame(self):
        """Take a screenshot -> (when it was taken, lines)."""
        t0 = time.perf_counter()
        img = self.grab(self.grid.box)
        t1 = time.perf_counter()
        lines = self.grid.lines(img)
        if self.recent is not None:
            self.recent.append(((t0 + t1) / 2, img[::2, ::2, :3].copy()))
        self.frame_time += 0.05 * (time.perf_counter() - t0 - self.frame_time)
        return (t0 + t1) / 2, lines

    def play_row(self):
        """Find the row that's moving, measure it, and click at the right moment."""
        self.row, self.recent = None, deque(maxlen=400)
        # per line and piece size: first column and time of the last solid piece seen
        self.memo_first = np.full((len(self.grid.ys), COLS + 1), -1)
        self.memo_time = np.full((len(self.grid.ys), COLS + 1), -np.inf)
        give_up = time.perf_counter() + 6
        while not self.quit and time.perf_counter() < give_up:
            t, lines = self.frame()
            if self.row is None:
                self.find_row(lines, t)
            elif t - self.last_move > 1.0:
                self.row = None  # nothing moving where we looked, look again
            else:
                self.track(t, cells(lines, self.row))
                now = time.perf_counter()
                plan = self.plan(now)
                # click from here if the next screenshot would come too late for it
                if plan and plan["click"] - now < SAFETY + 2 * self.frame_time:
                    self.fire(plan)
                    self.watch(plan)
                    return
        if not self.quit:
            self.log("no moving row found")
            self.save_debug()

    def save_debug(self, info=None, name="pyxdbet_debug.npz"):
        """Save what the bot just saw (and what it planned), so the problem can be looked at."""
        if not self.recent:
            return
        ts, imgs = zip(*self.recent)
        path = os.path.join(os.path.dirname(CONFIG), name)
        np.savez_compressed(path, t=np.array(ts), frames=np.stack(imgs),
                            box=list(self.grid.box.values()), info=json.dumps(info))
        self.log(f"saved the last {ts[-1] - ts[0]:.1f} s of what the bot saw to {path}")

    def find_row(self, lines, t):
        """The moving row is where lines show a solid piece of the same size as a moment
        ago, but in a different place. Each line is compared with the last time it showed
        a piece that size, so this also works if the row blinks, slides, or jumps cells."""
        count, first, solid = ends(lines > FULL)
        idx = np.flatnonzero(solid)
        size = count[idx]
        was, when = self.memo_first[idx, size], self.memo_time[idx, size]
        moved = idx[(was >= 0) & (was != first[idx]) & (t - when < 0.5)]
        self.memo_first[idx, size], self.memo_time[idx, size] = first[idx], t
        if len(moved) < 5:
            return
        y = float(np.median(self.grid.ys[moved]))
        row = self.grid.band(y)
        if row is None:
            return
        self.row, self.width, self.sizes = row, None, []  # width: measured over the next frames
        self.under = self.grid.ys > y + 0.5 * self.grid.py  # everything below the moving row
        self.below_band = self.grid.band(y + self.grid.py)
        self.below = self.below_span(lines)  # None if it's off the screen (or the first row)
        self.moves = []    # (time, position, direction, gap) every time the row slides a cell
        self.seen = None   # (time, position) from the last frame the whole row was visible
        self.last_move = self.found_at = t

    def below_span(self, lines):
        if self.below_band is None:
            return None
        idx = np.flatnonzero(cells(lines, self.below_band))
        return (int(idx[0]), int(idx[-1])) if len(idx) else None

    def track(self, t, row):
        self.trace.append((t, "".join("#" if c else "." for c in row)))
        s = span(row)
        if self.width is None:
            # How wide is the row? Use the size seen most often: while sliding between cells
            # (or blinking) it can look a block narrower for a moment.
            if s:
                self.sizes.append(s[1] - s[0] + 1)
            if len(self.sizes) >= 8 and t - self.last_move > 0.15:
                self.width = max(set(self.sizes), key=self.sizes.count)
                # Row below not on the screen (scrolled away)? Use where our last row landed,
                # unless this row is wider: rows only get narrower, so that's a new game.
                last = self.last_placed
                if self.below is None and last and self.width <= last[1] - last[0] + 1:
                    self.below = last
            return
        if s is None or s[1] - s[0] + 1 != self.width:
            return  # not the whole row visible in this frame
        if self.seen and s[0] != self.seen[1]:
            # it moved somewhere between the last frame we saw it whole and this one
            gap = t - self.seen[0]
            self.moves.append(((self.seen[0] + t) / 2, s[0], s[0] - self.seen[1], gap))
            self.last_move = t
            del self.moves[:-20]
        self.seen = (t, s[0])

    def beat(self):
        """Fit the moves to a steady beat: the n-th cell moved happens at a + n*T.
        Returns the fitted time of the last move and the step time T, or None."""
        moves = self.moves[-12:]
        for _ in range(2):
            if len(moves) >= 2:
                ts = np.array([m[0] for m in moves])
                n = np.cumsum([abs(m[2]) for m in moves])
                gaps = np.array([m[3] for m in moves])  # how unsure each move's time is
                T, a = np.polyfit(n, ts, 1, w=1 / np.maximum(gaps, self.frame_time))
                if T > 0 and (np.abs(ts - a - n * T) < 0.4 * T + 0.012 + gaps / 2).all():
                    return a + n[-1] * T, T
            # not steady (maybe it waits at the walls): use only the moves since it last turned
            k = len(moves) - 1
            while k > 0 and (moves[k - 1][2] > 0) == (moves[-1][2] > 0):
                k -= 1
            moves = moves[k:]
        return None

    def frames(self):
        """Games draw 60 frames a second, so each move shows up on a frame. Every move showed
        up between two of our screenshots, so a frame must fall inside that gap: find the
        60 Hz rhythm that fits (nearly) all the moves. Returns (frame length, a frame start,
        the frame each of the last 12 moves showed up on, which of those are certain) or None."""
        moves = self.moves[-12:]
        if len(moves) < 6:
            return None
        P, slack = 1 / 60, 0.002  # slack: we don't know exactly when inside a screenshot it was taken
        lo = np.array([m[0] - m[3] / 2 for m in moves]) - slack  # it showed up after this...
        hi = np.array([m[0] + m[3] / 2 for m in moves]) + slack  # ...and by this time
        ok = hi - lo < P  # a gap shorter than a frame holds just one frame
        if ok.sum() < 6:
            return None
        phases = np.arange(0, P, 0.0002)
        fits = (hi[ok, None] - phases) % P < (hi - lo)[ok, None]  # a frame falls in the gap
        score = fits.sum(axis=0)
        if score.max() < 0.9 * ok.sum():
            return None  # the moves don't follow a 60 Hz rhythm
        best = phases[score == score.max()]  # every rhythm that fits: use the middle one
        phase = float(np.angle(np.exp(2j * np.pi * best / P).mean()) / (2 * np.pi) * P)
        shown = phase + P * np.floor((hi - phase) / P)  # the frame each move showed up on
        return P, phase, shown, ok & (shown > lo)

    def timing(self):
        """How the moves are spaced in time. Returns (at, T): T is the step time and
        at(j) gives, for the j-th spot from now, (sure_start, sure_end, may_start, may_end,
        best): when the row is surely there, the longest it might be there, and the best
        single guess (start, end)."""
        fit = self.beat()
        if fit is None:
            return None
        t_last, T = fit
        grid = self.frames()
        if grid and (exact := self.frame_timing(grid)):
            return exact

        def at(j):
            a, b = t_last + j * T, t_last + (j + 1) * T
            return a, b, a, b, (a, b)
        return at, T

    def frame_timing(self, grid):
        """With a 60 Hz rhythm each move shows up on the first frame after it really
        happens, which pins down its real time to within one frame. We keep every step
        time T (and start time) that fits all the moves we saw, and from those work out
        the earliest and latest frame each future move can show up on."""
        P, phase, shown, sharp = grid
        moves = self.moves[-12:]
        n = np.cumsum([abs(m[2]) for m in moves])  # move number (one per cell)
        last = n[-1]                               # the move that brought it where it is now
        if sharp.sum() < 4:
            return None
        n, shown = n[sharp], shown[sharp]
        # Two moves k steps apart that showed up d apart: k*T is between d - P and d + P.
        i, j = np.triu_indices(len(n), 1)
        k, d = n[j] - n[i], shown[j] - shown[i]
        T_lo, T_hi = ((d - P) / k).max(), ((d + P) / k).min()
        if T_lo >= T_hi:
            return None  # doesn't fit a steady beat on steady frames
        frames = max(1, round((T_lo + T_hi) / 2 / P))
        if np.ptp(shown - n * frames * P) < P / 2:
            Ts = np.array([[frames * P]])  # every move came exactly so many frames apart: use that
        else:
            Ts = np.linspace(T_lo, T_hi, 102)[1:-1, None]
        r = shown - n * Ts  # for each T: when move 0 happened is in (max(r) - P, min(r)]
        lo, hi = r.max(axis=1) - P, r.min(axis=1)
        Ts = Ts[:, 0]

        def frame(x):  # the first frame at or after time x
            return float(phase + P * np.ceil((x - phase) / P - 1e-6))

        def shows_up(k):  # earliest and latest time move k (counted like n) can show up
            return frame((lo + k * Ts).min() + 1e-6), frame((hi + k * Ts).max())

        mid = len(Ts) // 2  # the middle of everything that fits: the best single guess
        best_start, best_T = (lo[mid] + hi[mid]) / 2, Ts[mid]

        def at(j):
            first, nxt = shows_up(last + j), shows_up(last + j + 1)
            best = (frame(best_start + (last + j) * best_T), frame(best_start + (last + j + 1) * best_T))
            return first[1], nxt[0], first[0], nxt[1], best
        return at, float(Ts.mean())

    def plan(self, now):
        """When to click so the row stops lined up with the one below it."""
        if len(self.moves) < MIN_MOVES or not (timing := self.timing()):
            return None
        at, T = timing
        if len(self.moves) < min(10, 0.3 / T):
            return None  # fast row: watch a few more moves so the speed is exact
        p, d = self.moves[-1][1:3]
        d = 1 if d > 0 else -1
        W = self.width
        wall = COLS - W if d > 0 else 0
        steps = (wall - p) * d  # moves left before it hits the wall and turns around
        if self.below:
            lo, hi = sorted((self.below[0], self.below[1] - W + 1))
        else:  # first row: anywhere, but stay off the walls
            lo, hi = (1, COLS - W - 1) if COLS - W >= 2 else (0, COLS - W)
        row = self.row_number(W, self.below)
        side = self.side(row, W, lo, hi)
        # j moves from now the row is at p + j*d
        js = [j for j in range(steps + 1) if lo <= p + j * d <= hi]
        while js:
            if side and not any(p + j * d in side for j in js) and now - self.found_at < 3:
                return None  # its spot at the side isn't coming on this pass: wait for it
            wins = [at(j) for j in js]
            if all(w[1] <= w[0] for w in wins) and now - self.found_at <= 1.0:
                js.pop(0)  # not sure when it's there, wait for a spot we are sure about
                continue
            # every good spot keeps all the blocks, the one at the side counts a bit more
            worth = [1.0 if not side or p + j * d in side else 0.95 for j in js]
            best = self.best_click(wins, self.spread(row), now + SAFETY, worth)
            if best:
                aim = (wins[0][0] + wins[-1][1]) / 2  # the middle of the good spots
                return dict(click=best[0], chance=best[1], aim=aim, used=aim - best[0], row=row,
                            side=side, at=at, T=T, p=p, d=d, j0=js[0], j1=js[-1], steps=steps,
                            t_ref=self.moves[-1][0])
            js.pop(0)  # too soon, try a later spot
        return None  # wait for it to come back the other way

    def side(self, row, W, lo, hi):
        """While the tower narrows, where this row should stop (a set of left ends) so the
        tower stands SIDE columns in from a side: its left end at column SIDE, or its right
        end at column COLS-1-SIDE (for the first row either, then the side the tower is
        on). None: no preference."""
        if SIDE is None or row >= START_WIDTH or lo >= hi:
            return None
        if self.below is None:
            want = (SIDE, COLS - SIDE - W)
        elif self.below[0] - SIDE <= COLS - 1 - SIDE - self.below[1]:
            want = (SIDE,)
        else:
            want = (COLS - SIDE - W,)
        # as close as possible, if the tower isn't quite there
        return {min(range(lo, hi + 1), key=lambda q: abs(q - w)) for w in want}

    def fire(self, plan):
        # wait without keeping the CPU busy, then time the last moment exactly
        while (left := plan["click"] - time.perf_counter()) > 0.002:
            time.sleep(left - 0.0015)
        while time.perf_counter() < plan["click"]:
            pass
        plan["t"] = time.perf_counter()
        self.press()
        plan.update(W=self.width, below=self.below)
        self.count(plan["row"], self.width)
        time.sleep(QUIET)  # leave the PC alone while the game handles the click
        self.last_move = time.perf_counter()  # look again before deciding it has stopped

    def edges(self, lines):
        """Top and bottom line of the moving row, to notice the screen scrolling."""
        lit = (lines > FULL).any(axis=1)
        idx = np.flatnonzero(self.row)
        top = bottom = idx[len(idx) // 2]
        while top > 0 and lit[top - 1]:
            top -= 1
        while bottom < len(lit) - 1 and lit[bottom + 1]:
            bottom += 1
        return top, bottom

    def watch(self, s):
        """Keep looking for a moment to see where the row stopped, and learn from it."""
        settled, ref, t, empty_since = None, None, s["t"], None
        end = s["t"] + max(0.6, 3 * s["T"] + 0.1)
        while not self.quit and t < end:
            t, lines = self.frame()
            if ref is None:  # how things looked right after the click
                ref, ref_edges = lines, self.edges(lines)
            row = cells(lines, self.row)
            self.track(t, row)
            empty_since = (empty_since or t) if row.sum() == 0 else None
            was = np.zeros(COLS, bool)  # where we last saw the whole row: cutting only removes
            was[self.seen[1]:self.seen[1] + s["W"]] = True
            if self.last_move == t:
                settled = None  # still moving
            elif (row & ~was).any():
                pass            # something else is in the way (the screen scrolling?)
            elif 0 < row.sum() < s["W"] and span(row):
                settled = row   # part of it was cut off, so it has stopped
            elif empty_since is not None and t - empty_since > 0.1:
                settled = row   # all of it fell off (gone for a while, not just blinking)
            elif row.sum() and t - self.last_move > 1.3 * s["T"] + 0.005:
                settled = row   # a move was due and didn't come, so it has stopped
            top, bottom = self.edges(lines)
            if (((lines[self.under] > FULL) != (ref[self.under] > FULL)).any(axis=1).sum() > 3
                    or abs(top - ref_edges[0]) > 2 or abs(bottom - ref_edges[1]) > 2):
                break  # the screen is scrolling or something is falling: stop looking
            if settled is not None and t > s["t"] + s["used"] + 2 * s["T"]:
                break
        # remember where it landed, for when the row below scrolls off the screen
        if settled is not None and span(settled):
            self.last_placed = span(settled)
        elif self.seen:
            self.last_placed = (self.seen[1], self.seen[1] + s["W"] - 1)
        outcome = self.check_shot(s, settled) if settled is not None else None
        if settled is None and t >= end:
            self.log("the row kept moving - is the mouse on the stop button?")
        self.write_log(s, outcome)
        for row in (s["row"] + 1, 0):  # work out the next row's delays now, not while timing it
            self.spread(row)

    def check_shot(self, s, row):
        idx = np.flatnonzero(row)
        W, below, kept = s["W"], s["below"], len(idx)
        if kept == W and span(row):
            p = int(idx[0])
        elif kept == 0 and self.seen:
            p = self.seen[1]  # the whole row fell off: it was last seen here
        elif span(row) and below and kept < W and (idx[0], idx[-1]) != below:
            L, R = int(idx[0]), int(idx[-1])
            if L == below[0]:
                p = R - W + 1  # the part hanging off the left was cut off
            elif R == below[1]:
                p = L          # the part hanging off the right was cut off
            else:
                return
        else:
            return
        # only the part that sits on the row below stays (it may still be falling off here)
        on = W if not below else max(0, min(p + W - 1, below[1]) - max(p, below[0]) + 1)
        result = "perfect" if on == W else "missed" if on == 0 else f"lost {W - on}"
        j = (p - s["p"]) * s["d"]  # it stopped j spots after where it was when we planned
        bounced = any((m[2] > 0) != (s["d"] > 0) for m in self.moves if m[0] > s["t_ref"])
        if not bounced and 0 <= j <= s["steps"]:
            # the click took effect while the block was on that spot: remember when that was
            _, _, start, end, _ = s["at"](j)
            if j == s["steps"]:
                end = start + 2 * s["T"]  # it may wait at the wall, so only the start is sure
            self.delays.setdefault(s["row"], []).append((start - s["t"], end - s["t"]))
            self.spreads = {}
            if j > s["j1"] or j < s["j0"]:
                result += " (late)" if j > s["j1"] else " (early)"
        self.log(f"row {s['row']} ({W} block{'s' if W > 1 else ''} at {s['T'] * 1000:.0f} ms): "
                 f"{result}, chance was {100 * s['chance']:.0f}%, latency for this row now "
                 f"{1000 * self.lat(s['row'], s['T'])[0]:.0f} ms")
        if on < W:  # save what happened, so the timing can be checked
            f = float
            self.save_debug(dict(
                result=result, clicked=f(s["t"]), planned=f(s["click"]), aim=f(s["aim"]),
                T=f(s["T"]), W=W, below=below, start=s["p"], d=s["d"], target=(s["j0"], s["j1"]),
                steps=s["steps"], stopped=p, j=j, bounced=bounced, frame_time=f(self.frame_time),
                windows=[[f(v) for v in s["at"](k)[:4]] for k in range(s["steps"] + 1)],
                moves=[[f(m[0]), int(m[1]), int(m[2]), f(m[3])] for m in self.moves]),
                name="pyxdbet_miss.npz")
        return dict(stopped=p, j=j, kept=kept, result=result, bounced=bounced)

    def write_log(self, s, outcome):
        """One line per click in pyxdbet_log.txt: to check the timing later, and the bot reads
        the recent ones back at start to know how the click delay is spread."""
        c = s["t"]
        # for each spot: when the block is surely there, and the widest it may be there
        wins = [[round((v - c) * 1000, 1) for v in s["at"](k)[:4]] for k in range(s["steps"] + 1)]
        if outcome and outcome["j"] == s["steps"]:  # the wall spot: only its start is sure
            wins[-1][3] = round(wins[-1][2] + 2000 * s["T"], 1)
        rec = dict(when=time.strftime("%H:%M:%S"), row=s["row"], W=s["W"], T=round(s["T"] * 1000, 1),
                   below=s["below"], start=s["p"], d=s["d"], target=[s["j0"], s["j1"]],
                   latency=round(s["used"] * 1000, 1), chance=round(s["chance"], 2),
                   **(outcome or {"result": "not seen"}),
                   windows=wins,
                   trace=[[round((t - c) * 1000, 1), r] for t, r in self.trace if -0.15 < t - c < 0.4])
        try:
            with open(LOG, "a") as f:
                f.write(json.dumps(rec) + "\n")
        except OSError:
            pass

    def arm(self):
        self.armed = True

    def adjust(self, dt):
        self.nudge += dt
        self.log(f"clicking {1000 * self.nudge:+.0f} ms earlier than the bot would")

    def stop(self):
        self.quit = True


def show(grid, lines):
    for r in range(grid.rows - 1, -1, -1):
        band = grid.band(grid.bottom - r * grid.py)
        row = cells(lines, band) if band is not None else np.zeros(COLS, bool)
        print(f"row {r:2d}  " + " ".join("#" if c else "." for c in row))


def main():
    cfg = load_config()
    if cfg is None or "calibrate" in sys.argv:
        cfg = calibrate(cfg)
    grid = Grid(cfg)
    with mss.mss() as sct:
        def grab(box):
            return np.asarray(sct.grab(box))

        if "check" in sys.argv:
            show(grid, grid.lines(grab(grid.box)))
            print("latency:", round(cfg["latency"] * 1000), "ms")
            return
        bot = Bot(grid, grab, click, cfg["latency"])
        speeds = bot.load_history()
        if bot.delays:
            print(f"Learned from {sum(map(len, bot.delays.values()))} earlier clicks (in {LOG}):")
            for row in sorted(speeds):
                delays, p = bot.spread(row)
                lo, hi = delays[np.cumsum(p).searchsorted([0.1, 0.9])]
                print(f"  row {row:2d}: {len(bot.delays.get(row, [])):3d} clicks, latency "
                      f"{1000 * bot.lat(row, speeds[row])[0]:3.0f} ms (the delay is mostly "
                      f"{1000 * lo:.0f}-{1000 * hi:.0f} ms)")
        corners = []

        def corner():
            """F8: reselect the grid - first the bottom-left cell, then the top-right cell."""
            if corners and time.perf_counter() - corners[0][1] > 15:
                corners.clear()  # the first press was too long ago, start over
            corners.append((getcoords(), time.perf_counter()))
            if len(corners) == 1:
                print("  new grid: now the MIDDLE of the TOP-RIGHT cell, then F8")
                return
            new = make_config(corners[0][0], corners[1][0], cfg)
            corners.clear()
            if new is None:
                print("  those don't look like the bottom-left and top-right cells, try again")
                return
            cfg.update(new)
            save_config(cfg)
            bot.new_grid = Grid(cfg)  # the bot switches over as soon as it's free
            print(f"  new grid: {COLS} columns x {cfg['rows']} rows, cells {cfg['pitch_x']:.1f}px")

        keyboard.add_hotkey(TRIGGER, bot.arm)
        keyboard.add_hotkey("f8", corner)
        keyboard.add_hotkey("plus", bot.adjust, args=(0.005,))
        keyboard.add_hotkey("-", bot.adjust, args=(-0.005,))
        keyboard.add_hotkey("esc", bot.stop)
        print(f"Ready. Put the mouse on the stop button and press {TRIGGER.upper()} while a row is moving.\n"
              "To reselect the grid: F8 on the MIDDLE of the BOTTOM-LEFT cell, then F8 on the TOP-RIGHT one.\n"
              "Numpad +/- click earlier/later, Esc quits.")
        bot.run()  # what it learns is kept in pyxdbet_log.txt, read back at the next start


if __name__ == "__main__":
    main()
