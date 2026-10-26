from __future__ import annotations

import argparse
import math
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from clusterai import MLP, ClusterNet

PROGRESSIVE_ALPHA = 0.5
SETTLE_TOL = 1e-3
MAX_LOOPS = 200
LOOP_TIE = 0.01


def join(*parts):
    return tuple(np.concatenate(arrays) for arrays in zip(*parts))


def make_parity(rng, n, dim, max_bits, min_bits=1):
    bits = rng.integers(min_bits, max_bits + 1, n)
    rank = rng.random((n, dim)).argsort(1).argsort(1)
    signs = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), (n, dim))
    X = (signs * (rank < bits[:, None])).astype(np.float32)
    y = ((X == 1).sum(1) % 2).astype(np.int64)
    return X, y, bits


def task_parity(rng, dim=32, train_bits=16, n_train=100_000, n_val=4_000, n_test=8_000):
    X_train, y_train, _ = make_parity(rng, n_train, dim, train_bits)
    X_val, y_val, d_val = join(make_parity(rng, n_val // 2, dim, train_bits),
                               make_parity(rng, n_val // 2, dim, train_bits + 1, train_bits + 1))
    X_test, y_test, d_test = make_parity(rng, n_test, dim, dim)
    return dict(X_train=X_train, y_train=y_train,
                X_val=X_val, y_val=y_val, difficulty_val=d_val,
                X_test=X_test, y_test=y_test, difficulty_test=d_test,
                question="is the number of +1s odd?", difficulty_name="number of +-1 bits",
                seen_up_to=train_bits,
                title_test="test set",
                buckets_test=[(1, 8), (9, 16), (18, 25), (26, 32)],
                hidden=128, train_loops=10, test_loops=[5, 10, 20, 30, 50, 100],
                epochs=60, batch=256, lr=3e-3)


def random_graphs(rng, count, n_nodes):
    position = rng.random((count, n_nodes)).argsort(1)
    gap = np.abs(position[:, :, None] - position[:, None, :])
    link_chance = np.select([gap == 1, gap == 2], [0.9, 0.1], default=0.01)
    adj = np.triu(rng.random(gap.shape) < link_chance, 1)
    return adj | adj.transpose(0, 2, 1)


def spread_from_node0(adj):
    count, n_nodes, _ = adj.shape
    reached = np.zeros((count, n_nodes), dtype=bool)
    reached[:, 0] = True
    step = np.where(reached, 0, -1)
    for t in range(1, n_nodes):
        reached = reached | (adj & reached[:, None, :]).any(2)
        step[reached & (step < 0)] = t
    return step


def make_reach(rng, n, n_nodes, max_difficulty, min_difficulty=1):
    if max_difficulty > n_nodes - 2:
        raise ValueError(f"max_difficulty can be at most n_nodes - 2 = {n_nodes - 2}")
    difficulties = range(min_difficulty, max_difficulty + 1)
    per_difficulty = n // (2 * len(difficulties))
    last = n_nodes - 1
    upper = np.triu_indices(n_nodes, 1)
    batch = max(1_000, 10_000_000 // n_nodes ** 2)
    waiting = {}
    pairs = {d: [] for d in difficulties}
    while any(len(p) < per_difficulty for p in pairs.values()):
        adj = random_graphs(rng, batch, n_nodes)
        step = spread_from_node0(adj)
        answer = step[:, last] >= 0
        depth = np.where(answer, step[:, last], step.max(1)).clip(min=1)
        keys = zip(depth.tolist(), answer.tolist(), adj.sum((1, 2)).tolist(),
                   adj[:, 0].sum(1).tolist(), adj[:, last].sum(1).tolist())
        for i, (d, yes, n_edges, links0, links_last) in enumerate(keys):
            if d not in pairs or len(pairs[d]) >= per_difficulty:
                continue
            slot = waiting.setdefault((d, n_edges, links0, links_last), ([], []))
            if slot[not yes]:
                partner = slot[not yes].pop()
                pairs[d].append((adj[i][upper], partner) if yes else (partner, adj[i][upper]))
            else:
                slot[yes].append(adj[i][upper])
    X = [graph for d in pairs for pair in pairs[d] for graph in pair]
    y = [1, 0] * (len(X) // 2)
    difficulty = [d for d in pairs for _ in range(2 * len(pairs[d]))]
    order = rng.permutation(len(X))
    return (np.array(X, dtype=np.float32)[order], np.array(y, dtype=np.int64)[order],
            np.array(difficulty)[order])


def task_reach(rng, n_nodes=14, train_difficulty=5, test_difficulty=11, big_nodes=20,
               big_difficulty=14, n_train=20_000, n_val=4_000, n_test=8_000, n_big=4_000):
    X_train, y_train, _ = make_reach(rng, n_train, n_nodes, train_difficulty)
    X_val, y_val, d_val = join(
        make_reach(rng, n_val // 2, n_nodes, train_difficulty),
        make_reach(rng, n_val // 2, n_nodes, train_difficulty + 1, train_difficulty + 1))
    X_test, y_test, d_test = make_reach(rng, n_test, n_nodes, test_difficulty)
    X_big, y_big, d_big = make_reach(rng, n_big, big_nodes, big_difficulty)
    return dict(X_train=X_train, y_train=y_train,
                X_val=X_val, y_val=y_val, difficulty_val=d_val,
                X_test=X_test, y_test=y_test, difficulty_test=d_test,
                X_big=X_big, y_big=y_big, difficulty_big=d_big,
                question=f"is there a path from node 0 to the last node?",
                difficulty_name="spreading steps needed", seen_up_to=train_difficulty, graph=True,
                title_test=f"test set: {n_nodes}-node graphs (same size as training)",
                title_big=f"bigger graphs: {big_nodes} nodes (trained on {n_nodes}) - "
                          f"only models that can take a different input size",
                buckets_test=[(1, 3), (4, 5), (7, 8), (9, 11)],
                buckets_big=[(1, 5), (7, 10), (11, 14)],
                hidden=256, train_loops=6, test_loops=[3, 6, 12, 24, 48, 96],
                epochs=60, batch=256, lr=3e-3)


TASKS = {"parity": task_parity, "reach": task_reach}


class FlatCluster(ClusterNet):

    def __init__(self, n_in, n_cluster):
        super().__init__(n_in, n_cluster, 2, adaptive=False)

    def begin(self, x):
        drive = self.input_weights(x)
        return drive, torch.zeros_like(drive)

    def loop(self, drive, h, loops):
        for _ in range(loops):
            h = torch.tanh(self.cluster_weights(h) + drive)
        return h

    def answer(self, h):
        return self.output_layer(h)


class WiredCluster(nn.Module):

    def __init__(self, group_size=32):
        super().__init__()
        self.group_size = group_size
        self.own = nn.Linear(group_size, group_size)
        self.message = nn.Linear(group_size, group_size, bias=False)
        self.role = nn.Parameter(0.5 * torch.randn(3, group_size))
        self.output_layer = nn.Linear(group_size, 2)

    def begin(self, x):
        n = round((1 + math.sqrt(1 + 8 * x.shape[1])) / 2)
        rows, cols = torch.triu_indices(n, n, 1, device=x.device)
        adj = x.new_zeros(len(x), n, n)
        adj[:, rows, cols] = x
        roles = torch.full((n,), 2, device=x.device)
        roles[0], roles[-1] = 0, 1
        context = (adj + adj.transpose(1, 2), self.role[roles])
        return context, x.new_zeros(len(x), n, self.group_size)

    def loop(self, context, h, loops):
        adj, role = context
        for _ in range(loops):
            h = torch.tanh(self.own(h) + torch.bmm(adj, self.message(h)) + role)
        return h

    def answer(self, h):
        return self.output_layer(h[:, -1])


MODEL_NAMES = ["mlp", "cluster", "cluster-progressive", "wired", "wired-progressive"]


def build_model(name, data):
    n_in = data["X_train"].shape[1]
    if name == "mlp":
        return MLP(n_in, data["hidden"], 2)
    if name.startswith("wired"):
        return WiredCluster()
    return FlatCluster(n_in, data["hidden"])


def predict(model, x, loops=None):
    if isinstance(model, MLP):
        return model.layers(x)
    context, h = model.begin(x)
    return model.answer(model.loop(context, h, loops))


@torch.no_grad()
def predict_settle(model, x):
    context, h = model.begin(x)
    answers = model.answer(h)
    loops_used = torch.full((len(x),), MAX_LOOPS, device=x.device)
    running = torch.ones(len(x), dtype=torch.bool, device=x.device)
    for loop in range(1, MAX_LOOPS + 1):
        new_h = model.loop(context, h, 1)
        answers[running] = model.answer(new_h)[running]
        moved = (new_h - h).abs().flatten(1).amax(1)
        settled = running & (moved < SETTLE_TOL) & (loop > 1)
        loops_used[settled] = loop
        running &= ~settled
        h = new_h
        if not running.any():
            break
    return answers, loops_used


@torch.no_grad()
def correct_answers(model, X, y, loops, device):
    model.eval()
    X = torch.as_tensor(X, device=device)
    y = torch.as_tensor(y, device=device)
    if loops == "settle":
        answers, used = predict_settle(model, X)
        return (answers.argmax(-1) == y).cpu().numpy(), used.float().cpu().numpy()
    return (predict(model, X, loops).argmax(-1) == y).cpu().numpy(), None


def validation_score(model, data, loops, device):
    correct, _ = correct_answers(model, data["X_val"], data["y_val"], loops, device)
    harder = data["difficulty_val"] > data["seen_up_to"]
    return (correct[~harder].mean() + correct[harder].mean()) / 2


def checkpoint_score(model, data, device):
    if isinstance(model, MLP):
        return validation_score(model, data, None, device)
    t = data["train_loops"]
    return max(validation_score(model, data, n, device) for n in (t, 2 * t, 4 * t))


def pick_loops(model, data, device):
    scores = {n: validation_score(model, data, n, device) for n in data["test_loops"]}
    best = max(scores.values())
    return max(n for n, score in scores.items() if score >= best - LOOP_TIE)


def train(model, data, progressive, epochs, device):
    X = torch.as_tensor(data["X_train"], device=device)
    y = torch.as_tensor(data["y_train"], device=device)
    loops, batch = data["train_loops"], data["batch"]
    opt = torch.optim.Adam(model.parameters(), lr=data["lr"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(
        opt, T_max=epochs * math.ceil(len(X) / batch))

    best_score, best_epoch, best_state = -1.0, 0, None
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(X), device=device)
        for start in range(0, len(X), batch):
            idx = order[start:start + batch]
            xb, yb = X[idx], y[idx]
            loss = F.cross_entropy(predict(model, xb, loops), yb)
            if progressive:
                context, h = model.begin(xb)
                skip = int(torch.randint(0, loops, ()))
                more = int(torch.randint(1, loops - skip + 1, ()))
                with torch.no_grad():
                    h = model.loop(context, h, skip)
                restart_loss = F.cross_entropy(model.answer(model.loop(context, h, more)), yb)
                loss = (1 - PROGRESSIVE_ALPHA) * loss + PROGRESSIVE_ALPHA * restart_loss
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()

        score = checkpoint_score(model, data, device)
        if score > best_score:
            best_score, best_epoch = score, epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return best_epoch


def evaluate(model, data, split, picked_loops, device):
    X, y = data[f"X_{split}"], data[f"y_{split}"]
    d, buckets = data[f"difficulty_{split}"], data[f"buckets_{split}"]

    def per_bucket(values):
        return [values[(d >= lo) & (d <= hi)].mean() for lo, hi in buckets]

    if isinstance(model, MLP):
        return {None: dict(acc=per_bucket(correct_answers(model, X, y, None, device)[0]))}
    rows = {n: dict(acc=per_bucket(correct_answers(model, X, y, n, device)[0]))
            for n in data["test_loops"]}
    rows["picked"] = dict(acc=rows[picked_loops]["acc"], loops=picked_loops)
    correct, used = correct_answers(model, X, y, "settle", device)
    rows["settle"] = dict(acc=per_bucket(correct), loops=per_bucket(used))
    return rows


def print_results(data, results, split):
    buckets = data[f"buckets_{split}"]
    n_seen = sum(hi <= data["seen_up_to"] for _, hi in buckets)
    labels = [f"{lo}-{hi}" for lo, hi in buckets]

    def cells(values, fmt):
        return ("".join(f"{v:{fmt}}" for v in values[:n_seen]) + "   |"
                + "".join(f"{v:{fmt}}" for v in values[n_seen:]))

    print(f"\n  {data[f'title_{split}']}")
    print(f"  accuracy by {data['difficulty_name']} "
          f"(left of | = training difficulty, right of | = harder)")
    print(f"  {'model':<21}{'loops':>8}{cells(labels, '>8')}   harder avg")
    previous, harder_avg = None, {}
    for (name, row), per_seed in results.items():
        acc = np.mean([s["acc"] for s in per_seed], 0)
        harder = [np.mean(s["acc"][n_seen:]) for s in per_seed]
        harder_avg.setdefault(name, {})[row] = np.mean(harder)
        if row is None or isinstance(row, str):
            label = row or "-"
        else:
            label = ("*" if row == data["train_loops"] else "") + str(row)
        note = ("   loops picked: " + ", ".join(str(s["loops"]) for s in per_seed)
                if row == "picked" else "")
        print(f"  {name if name != previous else '':<21}{label:>8}{cells(acc, '>8.3f')}   "
              f"{np.mean(harder):.3f} +- {np.std(harder):.3f}{note}")
        if row == "settle":
            used = np.mean([s["loops"] for s in per_seed], 0)
            print(f"  {'':<21}{'loops:':>8}{cells(used, '>8.1f')}")
        previous = name
    print("  * = loop count used in training   picked = loop count chosen on validation\n"
          "  settle = each input loops until its state stops changing   guessing scores 0.500")

    print("\n  verdict on the harder problems (never used for any choice):")
    for name, rows in harder_avg.items():
        if None in rows:
            print(f"    {name:<21} {rows[None]:.3f}   (cannot loop)")
        else:
            print(f"    {name:<21} {rows[data['train_loops']]:.3f} at {data['train_loops']} loops   "
                  f"{rows['picked']:.3f} with loops picked on validation   "
                  f"{rows['settle']:.3f} looping until settled")


def main():
    parser = argparse.ArgumentParser(description="train easy, test hard")
    parser.add_argument("--tasks", nargs="+", choices=list(TASKS), default=list(TASKS))
    parser.add_argument("--models", nargs="+", choices=MODEL_NAMES, default=MODEL_NAMES)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--quick", action="store_true", help="10x fewer epochs, to check it runs")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    device = torch.device(args.device)
    if device.type == "cuda":
        nn.Linear(8, 8).to(device)(torch.randn(4, 8, device=device)).sum().backward()
        torch.cuda.synchronize()

    for task_name in args.tasks:
        start = time.perf_counter()
        data = TASKS[task_name](np.random.default_rng(0))
        epochs = max(1, data["epochs"] // 10) if args.quick else data["epochs"]
        print(f"\n=== {task_name}: {data['question']} ===")
        print(f"  trained on {data['difficulty_name']} up to {data['seen_up_to']}   "
              f"{len(data['X_train'])} train / {len(data['X_val'])} validation / "
              f"{len(data['X_test'])} test examples (made in {time.perf_counter() - start:.0f}s)")

        results = {"test": {}, "big": {}}
        for name in args.models:
            if name.startswith("wired") and not data.get("graph"):
                continue
            start = time.perf_counter()
            kept_epochs = []
            for seed in range(args.seeds):
                torch.manual_seed(seed)
                model = build_model(name, data).to(device)
                kept_epochs.append(train(model, data, name.endswith("-progressive"), epochs, device))
                picked = None if isinstance(model, MLP) else pick_loops(model, data, device)
                splits = ["test", "big"] if isinstance(model, WiredCluster) else ["test"]
                for split in splits:
                    for row, value in evaluate(model, data, split, picked, device).items():
                        results[split].setdefault((name, row), []).append(value)
            params = sum(p.numel() for p in model.parameters())
            print(f"  trained {name:<20} {params:>7,} weights   "
                  f"{(time.perf_counter() - start) / args.seeds:.0f}s per seed   "
                  f"kept epoch {', '.join(map(str, kept_epochs))} of {epochs} (best on validation)")

        for split in ("test", "big"):
            if results[split]:
                print_results(data, results[split], split)


if __name__ == "__main__":
    main()
