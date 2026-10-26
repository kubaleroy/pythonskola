from __future__ import annotations

import argparse
import math
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from clusterai import MLP

OPEN_CHANCE = 0.6
TRAIN_SIZE = 9
SEEN_UP_TO = 10
TRAIN_LOOPS = 12
TEST_LOOPS = [6, 12, 24, 48, 96, 192, 384]
MAX_LOOPS = 400
SETTLE_TOL = 1e-3
LOOP_TIE = 0.01
PROGRESSIVE_ALPHA = 0.5
BATCH = 256
NO_PATH = 10 ** 6
BUCKETS = {
    9: [(1, 5), (6, 10), (12, 16), (17, 24)],
    15: [(1, 10), (12, 30), (31, 50)],
    25: [(1, 10), (12, 50), (51, 100)],
    41: [(1, 10), (12, 80), (81, 200)],
}
WALL, OPEN, START, GOAL = 0, 1, 2, 3
MODELS = ["mlp", "count-neurons", "count-loops"]


def random_mazes(rng, count, size):
    grid = rng.random((count, size, size)) < OPEN_CHANCE
    keys = rng.random((count, size * size)) * grid.reshape(count, -1)
    start = keys.argmax(1)
    keys[np.arange(count), start] = 0
    goal = keys.argmax(1)
    keep = grid.reshape(count, -1).sum(1) >= 2
    return grid[keep], start[keep], goal[keep]


def flood(grid, cell):
    count = len(grid)
    reached = np.zeros(grid.shape, dtype=bool)
    reached.reshape(count, -1)[np.arange(count), cell] = True
    step = np.where(reached, 0, -1)
    t = 0
    while True:
        t += 1
        grow = np.zeros_like(reached)
        grow[:, 1:] |= reached[:, :-1]
        grow[:, :-1] |= reached[:, 1:]
        grow[:, :, 1:] |= reached[:, :, :-1]
        grow[:, :, :-1] |= reached[:, :, 1:]
        new = grow & grid & ~reached
        if not new.any():
            return step
        step[new] = t
        reached |= new


def make_mazes(rng, n, size, buckets, reachable=True):
    top = max(hi for _, hi in buckets)
    bucket_of = np.full(top + 2, -1)
    for b, (lo, hi) in enumerate(buckets):
        bucket_of[lo:hi + 1] = b
    per_bucket = n // len(buckets)
    chosen = [[] for _ in buckets]
    batch = max(200, 4_000_000 // size ** 2)
    for _ in range(2_000):
        if all(len(c) >= per_bucket for c in chosen):
            break
        grid, start, goal = random_mazes(rng, batch, size)
        count, rows = len(grid), np.arange(len(grid))
        from_start = flood(grid, start).reshape(count, -1)
        length = from_start[rows, goal]
        if reachable:
            depth = length
        else:
            from_goal = flood(grid, goal).reshape(count, -1)
            depth = np.where(length < 0, np.minimum(from_start.max(1), from_goal.max(1)), -1)
        mazes = np.where(grid, OPEN, WALL).astype(np.int8).reshape(count, -1)
        mazes[rows, start] = START
        mazes[rows, goal] = GOAL
        bucket = np.where(depth >= 0, bucket_of[np.clip(depth, 0, top + 1)], -1)
        for b in range(len(buckets)):
            take = np.flatnonzero(bucket == b)[:per_bucket - len(chosen[b])]
            chosen[b] += [(mazes[j].reshape(size, size), depth[j]) for j in take]
    else:
        raise RuntimeError(f"could not make enough {size}x{size} mazes for {buckets}")
    items = [item for c in chosen for item in c]
    order = rng.permutation(len(items))
    return (np.stack([items[k][0] for k in order]),
            np.array([items[k][1] for k in order], dtype=np.int64))


def make_data(rng, sizes, n_train=20_000, n_val=4_000, n_test=4_000, n_big=2_000, n_unreachable=1_000):
    train_buckets = [(d, d) for d in range(1, SEEN_UP_TO + 1)]
    data = {"train": make_mazes(rng, n_train, TRAIN_SIZE, train_buckets)}
    easy = make_mazes(rng, n_val // 2, TRAIN_SIZE, train_buckets)
    harder = make_mazes(rng, n_val // 2, TRAIN_SIZE, [(SEEN_UP_TO + 1, SEEN_UP_TO + 1)])
    data["val"] = tuple(np.concatenate(parts) for parts in zip(easy, harder))
    for size in sizes:
        data[size] = make_mazes(rng, n_test if size == TRAIN_SIZE else n_big, size, BUCKETS[size])
        data["no", size] = make_mazes(rng, n_unreachable, size, [(0, size * size)], reachable=False)
    data["train_no"] = make_mazes(rng, n_train // 4, TRAIN_SIZE, [(0, TRAIN_SIZE ** 2)], reachable=False)
    data["val_no"] = make_mazes(rng, n_unreachable, TRAIN_SIZE, [(0, TRAIN_SIZE ** 2)], reachable=False)
    return data


class GridCluster(nn.Module):
    def __init__(self, width=32):
        super().__init__()
        self.width = width
        self.own = nn.Linear(width, width)
        self.message = nn.Linear(width, width, bias=False)
        self.role = nn.Parameter(0.5 * torch.randn(3, width))
        self.output_layer = nn.Linear(width, 1)

    def begin(self, x):
        x = x.long()
        open_cells = (x != WALL).unsqueeze(-1).float()
        role = self.role[(x - OPEN).clamp(min=0)] * open_cells
        goal = (x == GOAL).flatten(1).float().argmax(1)
        return (open_cells, role, goal), torch.zeros(*x.shape, self.width, device=x.device)

    def loop(self, context, h, loops):
        open_cells, role, _ = context
        for _ in range(loops):
            sent = F.pad(self.message(h) * open_cells, (0, 0, 1, 1, 1, 1))
            received = sent[:, :-2, 1:-1] + sent[:, 2:, 1:-1] + sent[:, 1:-1, :-2] + sent[:, 1:-1, 2:]
            h = torch.tanh(self.own(h) + received + role) * open_cells
        return h

    def everywhere(self, h):
        return self.output_layer(h).squeeze(-1)

    def answer(self, context, h):
        return self.everywhere(h).flatten(1)[torch.arange(len(h), device=h.device), context[2]]


def flat(x):
    return torch.cat([(x != WALL).flatten(1), (x == START).flatten(1), (x == GOAL).flatten(1)], 1).float()


def straight_line_guess(X, depth, size):
    cells = X.reshape(len(X), -1)
    start, goal = (cells == START).argmax(1), (cells == GOAL).argmax(1)
    guess = np.abs(start // size - goal // size) + np.abs(start % size - goal % size)
    return [np.mean(guess[(depth >= lo) & (depth <= hi)] == depth[(depth >= lo) & (depth <= hi)])
            for lo, hi in BUCKETS[size]]


def loss_on(model, name, x, length):
    if isinstance(model, MLP):
        return F.mse_loss(model.layers(flat(x)).squeeze(-1), length)
    context, h = model.begin(x)
    if name == "count-loops":
        loss = 0.0
        for t in range(1, TRAIN_LOOPS + 1):
            h = model.loop(context, h, 1)
            loss = loss + F.binary_cross_entropy_with_logits(model.answer(context, h), (length < t).float())
        return loss / TRAIN_LOOPS
    loss = F.mse_loss(model.answer(context, model.loop(context, h, TRAIN_LOOPS)), length)
    skip = int(torch.randint(0, TRAIN_LOOPS, ()))
    more = int(torch.randint(1, TRAIN_LOOPS - skip + 1, ()))
    with torch.no_grad():
        h = model.loop(context, h, skip)
    restart = F.mse_loss(model.answer(context, model.loop(context, h, more)), length)
    return (1 - PROGRESSIVE_ALPHA) * loss + PROGRESSIVE_ALPHA * restart


@torch.no_grad()
def trace(model, X, device, checkpoints=(), max_loops=0, chunk=256):
    model.eval()
    if isinstance(model, MLP):
        outputs = [model.layers(flat(torch.as_tensor(X[i:i + chunk], device=device))).squeeze(-1).cpu()
                   for i in range(0, len(X), chunk)]
        return {"answer": torch.cat(outputs).numpy()}
    checkpoints = set(checkpoints)
    last = max([max_loops, *checkpoints])
    at = {t: [] for t in checkpoints}
    settled, settle_loops, reached_at = [], [], []
    for i in range(0, len(X), chunk):
        x = torch.as_tensor(X[i:i + chunk], device=device)
        context, h = model.begin(x)
        answer = model.answer(context, h)
        loops_used = torch.full((len(x),), max_loops, device=device)
        first_yes = torch.full((len(x),), -1, device=device)
        running = torch.ones(len(x), dtype=torch.bool, device=device)
        for t in range(1, last + 1):
            new_h = model.loop(context, h, 1)
            out = model.answer(context, new_h)
            if t in at:
                at[t].append(out.cpu())
            first_yes[(first_yes < 0) & (out > 0)] = t
            answer[running] = out[running]
            stop = running & ((new_h - h).abs().flatten(1).amax(1) < SETTLE_TOL) & (t > 1)
            loops_used[stop] = t
            running &= ~stop
            h = new_h
            if t >= max(checkpoints, default=0) and not running.any() and bool((first_yes >= 0).all()):
                break
        settled.append(answer.cpu())
        settle_loops.append(loops_used.cpu())
        reached_at.append(first_yes.cpu())
    return {"at": {t: torch.cat(v).numpy() for t, v in at.items()},
            "settled": torch.cat(settled).numpy(),
            "settle_loops": torch.cat(settle_loops).float().numpy(),
            "reached_at": torch.cat(reached_at).numpy()}


def validation_score(depth, correct):
    harder = depth > SEEN_UP_TO
    return (correct[~harder].mean() + correct[harder].mean()) / 2


def checkpoint_score(model, name, data, device):
    X, depth = data["val"]
    if isinstance(model, MLP):
        return validation_score(depth, np.rint(trace(model, X, device)["answer"]) == depth)
    if name == "count-loops":
        run = trace(model, X, device, max_loops=4 * TRAIN_LOOPS)
        dark = trace(model, data["val_no"][0], device, max_loops=4 * TRAIN_LOOPS)["reached_at"] < 0
        return (validation_score(depth, run["reached_at"] - 1 == depth) + dark.mean()) / 2
    run = trace(model, X, device, checkpoints=(TRAIN_LOOPS, 2 * TRAIN_LOOPS, 4 * TRAIN_LOOPS))
    return max(validation_score(depth, np.rint(out) == depth) for out in run["at"].values())


def pick_loops(model, data, device):
    X, depth = data["val"]
    run = trace(model, X, device, checkpoints=TEST_LOOPS)
    scores = {t: validation_score(depth, np.rint(run["at"][t]) == depth) for t in TEST_LOOPS}
    best = max(scores.values())
    return max(t for t, score in scores.items() if score >= best - LOOP_TIE)


def train(model, name, data, epochs, device):
    X, length = data["train"]
    if name == "count-loops":
        X = np.concatenate([X, data["train_no"][0]])
        length = np.concatenate([length, np.full(len(data["train_no"][0]), NO_PATH)])
    X = torch.as_tensor(X, device=device)
    length = torch.as_tensor(length, dtype=torch.float32, device=device)
    opt = torch.optim.Adam(model.parameters(), lr=3e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs * math.ceil(len(X) / BATCH))
    best_score, best_epoch, best_state = -1.0, 0, None
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(X), device=device)
        for start in range(0, len(X), BATCH):
            idx = order[start:start + BATCH]
            loss = loss_on(model, name, X[idx], length[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
        score = checkpoint_score(model, name, data, device)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return best_epoch


def evaluate(model, name, data, size, picked, device):
    X, depth = data[size]

    def per_bucket(values):
        return [values[(depth >= lo) & (depth <= hi)].mean() for lo, hi in BUCKETS[size]]

    if isinstance(model, MLP):
        return {"-": dict(acc=per_bucket(np.rint(trace(model, X, device)["answer"]) == depth))}
    if name == "count-loops":
        run = trace(model, X, device, max_loops=MAX_LOOPS)
        no_path = trace(model, data["no", size][0], device, max_loops=MAX_LOOPS)["reached_at"] < 0
        return {"counted": dict(acc=per_bucket(run["reached_at"] - 1 == depth), no_path=no_path.mean())}
    run = trace(model, X, device, checkpoints=(TRAIN_LOOPS, picked), max_loops=MAX_LOOPS)
    return {f"*{TRAIN_LOOPS}": dict(acc=per_bucket(np.rint(run["at"][TRAIN_LOOPS]) == depth)),
            "picked": dict(acc=per_bucket(np.rint(run["at"][picked]) == depth), loops=picked,
                           answers=per_bucket(run["at"][picked]), truth=per_bucket(depth)),
            "settle": dict(acc=per_bucket(np.rint(run["settled"]) == depth),
                           loops=per_bucket(run["settle_loops"]))}


def print_table(size, results):
    buckets = BUCKETS[size]
    n_seen = sum(hi <= SEEN_UP_TO for _, hi in buckets)
    labels = [f"{lo}-{hi}" for lo, hi in buckets]

    def cells(values, fmt):
        return ("".join(f"{v:{fmt}}" for v in values[:n_seen]) + "   |"
                + "".join(f"{v:{fmt}}" for v in values[n_seen:]))

    where = "training size" if size == TRAIN_SIZE else f"trained on {TRAIN_SIZE}x{TRAIN_SIZE}"
    print(f"\n  {size}x{size} mazes ({where}): exact path length, by true length "
          f"(left of | = lengths seen in training, right = longer)")
    print(f"  {'model':<15}{'loops':>8}{cells(labels, '>9')}   longer avg")
    previous = None
    for (name, row), per_seed in results.items():
        acc = np.mean([s["acc"] for s in per_seed], 0)
        longer = [np.mean(s["acc"][n_seen:]) for s in per_seed]
        note = ""
        if row == "picked":
            note = ("   loops picked: " + ", ".join(str(s["loops"]) for s in per_seed)
                    + f"   longest paths: answers {np.mean([s['answers'][-1] for s in per_seed]):.1f}"
                    + f" on average, true {np.mean([s['truth'][-1] for s in per_seed]):.1f}")
        if row == "counted":
            note = f"   no-path mazes left dark: {np.mean([s['no_path'] for s in per_seed]):.3f}"
        print(f"  {name if name != previous else '':<15}{row:>8}{cells(acc, '>9.3f')}   "
              f"{np.mean(longer):.3f} +- {np.std(longer):.3f}{note}")
        if row == "settle":
            print(f"  {'':<15}{'loops:':>8}{cells(np.mean([s['loops'] for s in per_seed], 0), '>9.1f')}")
        previous = name


def print_summary(sizes, results):
    print("\n  summary: exact length on paths longer than any seen in training (never used for any choice)")
    print(f"  {'model':<15}{'loops':>8}" + "".join(f"{f'{s}x{s}':>9}" for s in sizes))
    for name, row in dict.fromkeys(key for size in sizes for key in results[size]):
        line = ""
        for size in sizes:
            n_seen = sum(hi <= SEEN_UP_TO for _, hi in BUCKETS[size])
            per_seed = results[size].get((name, row))
            line += (f"{np.mean([np.mean(s['acc'][n_seen:]) for s in per_seed]):>9.3f}"
                     if per_seed else f"{'-':>9}")
        print(f"  {name:<15}{row:>8}{line}")
    print(f"  *{TRAIN_LOOPS} = loops used in training   picked = loop count chosen on validation   "
          f"settle = loop until the state stops changing\n"
          f"  counted = loops until the goal lights up, minus one   mlp only takes {TRAIN_SIZE}x{TRAIN_SIZE} mazes\n"
          f"  straight guess = rows apart + columns apart, ignoring walls (no learning, for reference)\n"
          f"  count-loops also trains on mazes with no path (it can say 'never reached'; a number neuron can't)")


@torch.no_grad()
def show_spreading(model, X, depth, device):
    pick = int(np.argmax(depth))
    maze, length = X[pick], int(depth[pick])
    size = len(maze)
    moments = sorted({max(1, (length + 1) // 3), max(2, 2 * (length + 1) // 3), length + 1})
    base = np.where(maze == GOAL, OPEN, maze).reshape(-1)
    cells = np.flatnonzero(base == OPEN)
    copies = np.repeat(base[None], len(cells), 0)
    copies[np.arange(len(cells)), cells] = GOAL
    true_steps = flood((maze != WALL)[None], np.flatnonzero(maze.reshape(-1) == START))[0].reshape(-1)
    model.eval()
    context, h = model.begin(torch.as_tensor(copies.reshape(-1, size, size), device=device))
    frames, agreement = {}, {}
    ever = torch.zeros(len(cells), dtype=torch.bool, device=device)
    for t in range(1, moments[-1] + 1):
        h = model.loop(context, h, 1)
        ever |= model.answer(context, h) > 0
        if t in moments:
            lit = np.zeros(size * size, dtype=bool)
            lit[cells] = ever.cpu().numpy()
            truth = (true_steps >= 0) & (true_steps <= t - 1)
            agreement[t] = np.mean(lit[cells] == truth[cells])
            frames[t] = lit.reshape(size, size)
    symbols = {WALL: "##", START: "S ", GOAL: "G "}
    print(f"\n  count-loops on a {size}x{size} maze whose shortest path is {length} steps: '..' = cells where it "
          f"has said 'reached' by then, if the goal were there")
    print("  " + "".join(f"after {t} loops ({agreement[t]:.0%} match)".ljust(2 * size + 4) for t in moments))
    for r in range(size):
        print("  " + "    ".join("".join(symbols.get(int(maze[r, c]), ".." if frames[t][r, c] else "  ")
                                          for c in range(size)) for t in moments).rstrip())


def main():
    parser = argparse.ArgumentParser(description="grid mazes: learn path lengths on small mazes, test on big ones")
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument("--sizes", nargs="+", type=int, choices=sorted(BUCKETS), default=sorted(BUCKETS))
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--quick", action="store_true", help="3 epochs and 1 seed, to check it runs")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    device = torch.device(args.device)
    epochs, seeds = (3, 1) if args.quick else (args.epochs, args.seeds)
    if device.type == "cuda":
        nn.Linear(8, 8).to(device)(torch.randn(4, 8, device=device)).sum().backward()
        torch.cuda.synchronize()

    start = time.perf_counter()
    data = make_data(np.random.default_rng(0), args.sizes)
    print("\n=== mazes: how many steps is the shortest path from S to G? ===")
    print(f"  trained on {TRAIN_SIZE}x{TRAIN_SIZE} mazes with paths of 1-{SEEN_UP_TO} steps, validated on "
          f"{SEEN_UP_TO + 1}-step paths, tested on {', '.join(f'{s}x{s}' for s in args.sizes)} "
          f"(made in {time.perf_counter() - start:.0f}s)")

    results = {size: {("straight guess", "-"): [dict(acc=straight_line_guess(*data[size], size))]}
               for size in args.sizes}
    example = None
    for name in args.models:
        start = time.perf_counter()
        kept = []
        for seed in range(seeds):
            torch.manual_seed(seed)
            model = (MLP(3 * TRAIN_SIZE ** 2, 256, 1) if name == "mlp" else GridCluster()).to(device)
            kept.append(train(model, name, data, epochs, device))
            picked = pick_loops(model, data, device) if name == "count-neurons" else None
            for size in args.sizes:
                if name == "mlp" and size != TRAIN_SIZE:
                    continue
                for row, value in evaluate(model, name, data, size, picked, device).items():
                    results[size].setdefault((name, row), []).append(value)
            if name == "count-loops" and seed == 0:
                example = model
        params = sum(p.numel() for p in model.parameters())
        print(f"  trained {name:<14} {params:>7,} weights   {(time.perf_counter() - start) / seeds:.0f}s per seed   "
              f"kept epoch {', '.join(map(str, kept))} of {epochs} (best on validation)")

    for size in args.sizes:
        if results[size]:
            print_table(size, results[size])
    print_summary(args.sizes, results)
    if example is not None:
        size = 15 if 15 in args.sizes else max(args.sizes)
        show_spreading(example, *data[size], device)


if __name__ == "__main__":
    main()
