from __future__ import annotations

import argparse
import math
import time

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

MAX_STEPS = 10
HALT_THRESHOLD = 0.5
PONDER_COST = 0.003
DECISION_BIAS = -2.0
STEP_FLOOR = 0.1
PONDER_WARMUP = 0.5


class ClusterNet(nn.Module):
    def __init__(self, n_in, n_cluster, n_out, adaptive=True, max_steps=MAX_STEPS):
        super().__init__()
        self.input_weights = nn.Linear(n_in, n_cluster)
        self.cluster_weights = nn.Linear(n_cluster, n_cluster, bias=False)
        self.output_layer = nn.Linear(n_cluster, n_out)
        nn.init.orthogonal_(self.cluster_weights.weight)
        self.adaptive = adaptive
        self.max_steps = max_steps
        if adaptive:
            self.decision = nn.Linear(n_cluster, 1)
            nn.init.constant_(self.decision.bias, DECISION_BIAS)

    def forward(self, x, stop_early=False):
        batch = x.shape[0]
        drive = self.input_weights(x)
        h = torch.zeros_like(drive)
        still_running = x.new_ones(batch)
        answers, stop_chance = [], []
        for step in range(self.max_steps):
            h = torch.tanh(self.cluster_weights(h) + drive)
            answers.append(self.output_layer(h))
            if step == self.max_steps - 1:
                decision = x.new_ones(batch)
            elif self.adaptive:
                decision = torch.sigmoid(self.decision(h)).squeeze(-1)
            else:
                decision = x.new_zeros(batch)
            stop_chance.append(still_running * decision)
            still_running = still_running * (1 - decision)
            if stop_early and bool((still_running <= 1 - HALT_THRESHOLD).all()):
                break
        return torch.stack(answers), torch.stack(stop_chance)

    @torch.no_grad()
    def predict(self, x):
        answers, stop_chance = self(x, stop_early=True)
        done = stop_chance.cumsum(0) >= HALT_THRESHOLD - 1e-4
        stop_step = done.float().argmax(0)
        return answers[stop_step, torch.arange(x.shape[0], device=x.device)], stop_step + 1


class MLP(nn.Module):

    def __init__(self, n_in, n_hidden, n_out, n_layers=2):
        super().__init__()
        self.n_layers = n_layers
        layers, width = [], n_in
        for _ in range(n_layers):
            layers += [nn.Linear(width, n_hidden), nn.ReLU()]
            width = n_hidden
        self.layers = nn.Sequential(*layers, nn.Linear(width, n_out))

    def forward(self, x, stop_early=False):
        return self.layers(x).unsqueeze(0), x.new_ones(1, x.shape[0])

    @torch.no_grad()
    def predict(self, x):
        return self.layers(x), None


MODEL_NAMES = ["mlp", "mlp-deep", "cluster-fixed", "cluster-adaptive"]


def mlp_params(n_in, width, n_out, n_layers):
    return (n_in + 1) * width + (n_layers - 1) * (width + 1) * width + (width + 1) * n_out


def build_model(name, n_in, n_hidden, n_out, args):
    if name == "mlp":
        return MLP(n_in, n_hidden, n_out, args.mlp_layers)
    if name == "mlp-deep":
        target = n_in * n_hidden + n_hidden + n_hidden ** 2 + (n_hidden + 1) * n_out
        width = max(w for w in range(1, n_hidden + 1)
                    if mlp_params(n_in, w, n_out, args.max_steps) <= target)
        return MLP(n_in, width, n_out, args.max_steps)
    return ClusterNet(n_in, n_hidden, n_out, adaptive=name == "cluster-adaptive",
                      max_steps=args.max_steps)


def task_parity(rng, dim=32, n_train=20_000, n_test=4_000):
    def make(n):
        length = rng.integers(1, dim + 1, n)
        bits = rng.choice(np.array([-1.0, 1.0], dtype=np.float32), (n, dim))
        X = bits * (np.arange(dim) < length[:, None])
        y = (X == 1).sum(1) % 2
        return X.astype(np.float32), y.astype(np.int64), length

    X_train, y_train, _ = make(n_train)
    X_test, y_test, length = make(n_test)
    return dict(X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
                kind="classify", n_out=2, hidden=128, epochs=60, batch=256, lr=3e-3,
                difficulty=length, difficulty_name="string length",
                buckets=[(q * dim // 4 + 1, (q + 1) * dim // 4) for q in range(4)])


def task_spirals(rng, n_train=4_000, n_test=2_000, turns=4.0, noise=0.02):
    def make(n):
        arm = rng.integers(0, 2, n)
        t = np.sqrt(rng.random(n)) * turns
        angle = 2 * np.pi * t + np.pi * arm
        r = (t + 0.1) / (turns + 0.1)
        X = np.stack([r * np.cos(angle), r * np.sin(angle)], 1)
        X += noise * rng.standard_normal((n, 2))
        return X.astype(np.float32), arm.astype(np.int64), t

    X_train, y_train, _ = make(n_train)
    X_test, y_test, t = make(n_test)
    return dict(X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test,
                kind="classify", n_out=2, hidden=32, epochs=150, batch=128, lr=3e-3,
                difficulty=t, difficulty_name="turns from centre",
                buckets=[(q * turns / 4, (q + 1) * turns / 4) for q in range(4)])


def task_digits(rng):
    from sklearn.datasets import load_digits

    X, y = load_digits(return_X_y=True)
    X = (X / 16.0).astype(np.float32)
    order = rng.permutation(len(X))
    cut = int(0.7 * len(X))
    train, test = order[:cut], order[cut:]
    return dict(X_train=X[train], y_train=y[train].astype(np.int64),
                X_test=X[test], y_test=y[test].astype(np.int64),
                kind="classify", n_out=10, hidden=64, epochs=100, batch=64, lr=3e-3)


def task_mackey(rng, length=8_000, tau=17, window=32, horizon=200, noise=0.0):
    warmup = 1_000
    x = np.full(length + warmup + tau, 1.2)
    for t in range(tau, len(x) - 1):
        x[t + 1] = x[t] + 0.2 * x[t - tau] / (1 + x[t - tau] ** 10) - 0.1 * x[t]
    x = x[warmup + tau:]
    cut = int(0.7 * len(x))
    x = (x - x[:cut].mean()) / x[:cut].std()
    x = (x + noise * rng.standard_normal(len(x))).astype(np.float32)

    n = len(x) - window - horizon + 1
    X = np.lib.stride_tricks.sliding_window_view(x, window)[:n]
    y = x[window + horizon - 1:][:, None]
    train_end = cut - window - horizon
    test_start = cut
    return dict(X_train=np.ascontiguousarray(X[:train_end]), y_train=y[:train_end],
                X_test=np.ascontiguousarray(X[test_start:]), y_test=y[test_start:],
                kind="regress", n_out=1, hidden=64, epochs=60, batch=128, lr=3e-3)


TASKS = {"parity": task_parity, "spirals": task_spirals,
         "digits": task_digits, "mackey": task_mackey}


def task_loss(answers, target, kind):
    steps = answers.shape[0]
    if kind == "classify":
        return F.cross_entropy(answers.flatten(0, 1), target.repeat(steps),
                               reduction="none").view(steps, -1)
    return ((answers - target) ** 2).mean(-1)


def train(model, data, args, device):
    X = torch.as_tensor(data["X_train"], device=device)
    y = torch.as_tensor(data["y_train"], device=device)
    epochs = max(1, data["epochs"] // 10) if args.quick else data["epochs"]
    batch = data["batch"]
    total = epochs * math.ceil(len(X) / batch)
    opt = torch.optim.Adam(model.parameters(), lr=data["lr"])
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=total)
    adaptive = getattr(model, "adaptive", False)

    model.train()
    it = 0
    for _ in range(epochs):
        order = torch.randperm(len(X), device=device)
        for start in range(0, len(X), batch):
            idx = order[start:start + batch]
            answers, stop_chance = model(X[idx])
            weight = stop_chance
            if adaptive:
                weight = (1 - STEP_FLOOR) * stop_chance + STEP_FLOOR / len(stop_chance)
            loss = (weight * task_loss(answers, y[idx], data["kind"])).sum(0).mean()
            if adaptive:
                ramp = min(1.0, it / (PONDER_WARMUP * total)) if PONDER_WARMUP > 0 else 1.0
                step_no = torch.arange(1, len(stop_chance) + 1, device=device).unsqueeze(1)
                loss = loss + args.ponder_cost * ramp * (stop_chance * step_no).sum(0).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            it += 1


@torch.no_grad()
def evaluate(model, data, device):
    model.eval()
    X = torch.as_tensor(data["X_test"], device=device)
    y = torch.as_tensor(data["y_test"], device=device)
    pred, steps = model.predict(X)
    steps = None if steps is None else steps.float().cpu().numpy()
    if data["kind"] == "classify":
        correct = (pred.argmax(-1) == y).cpu().numpy()
        return float(correct.mean()), correct, steps
    r2 = 1 - ((pred - y) ** 2).sum() / ((y - y.mean(0)) ** 2).sum()
    return float(r2), None, steps


def print_breakdown(data, per_model):
    d, buckets = data["difficulty"], data["buckets"]
    masks = [(d >= lo) & (d <= hi) for lo, hi in buckets]
    print(f"\n  accuracy by {data['difficulty_name']}:")
    print("  " + " " * 18 + "".join(f"{f'{lo:g}-{hi:g}':>10}" for lo, hi in buckets))
    for name, res in per_model.items():
        if res["correct"] is None:
            continue
        acc = np.mean(res["correct"], 0)
        print(f"  {name:<18}" + "".join(f"{acc[m].mean():>10.3f}" for m in masks))
        if res["steps"] is not None and name == "cluster-adaptive":
            st = np.mean(res["steps"], 0)
            print(f"  {'   avg steps':<18}" + "".join(f"{st[m].mean():>10.1f}" for m in masks))


def main():
    parser = argparse.ArgumentParser(description="ClusterNet vs a normal MLP")
    parser.add_argument("--tasks", nargs="+", choices=list(TASKS), default=list(TASKS))
    parser.add_argument("--models", nargs="+", choices=MODEL_NAMES, default=MODEL_NAMES)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--ponder-cost", type=float, default=PONDER_COST)
    parser.add_argument("--mlp-layers", type=int, default=2)
    parser.add_argument("--quick", action="store_true", help="10x fewer epochs, to check it runs")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()
    device = torch.device(args.device)
    if device.type == "cuda":
        nn.Linear(8, 8).to(device)(torch.randn(4, 8, device=device)).sum().backward()
        torch.cuda.synchronize()

    summary = []
    for task_name in args.tasks:
        data = TASKS[task_name](np.random.default_rng(0))
        metric = "accuracy" if data["kind"] == "classify" else "R2"
        n_in = data["X_train"].shape[1]
        print(f"\n=== {task_name}: {len(data['X_train'])} train / {len(data['X_test'])} test, "
              f"{metric} on test, hidden size {data['hidden']} ===")

        per_model = {}
        for name in args.models:
            scores, seconds, correct, steps = [], [], [], []
            for seed in range(args.seeds):
                torch.manual_seed(seed)
                model = build_model(name, n_in, data["hidden"], data["n_out"], args).to(device)
                start = time.perf_counter()
                train(model, data, args, device)
                if device.type == "cuda":
                    torch.cuda.synchronize()
                seconds.append(time.perf_counter() - start)
                score, c, s = evaluate(model, data, device)
                scores.append(score)
                correct.append(c)
                steps.append(s)

            params = sum(p.numel() for p in model.parameters())
            if isinstance(model, MLP):
                depth = f"{model.n_layers} layers"
            else:
                depth = f"{np.mean([s.mean() for s in steps]):.1f} steps"
            row = (task_name, name, f"{np.mean(scores):.3f} +- {np.std(scores):.3f}",
                   f"{params:,}", depth, f"{np.mean(seconds):.1f}")
            summary.append(row)
            print(f"  {name:<18} {metric} {row[2]}   params {row[3]:>7}   {depth:>11}   "
                  f"train {row[5]}s/seed")
            per_model[name] = dict(correct=None if correct[0] is None else correct, steps=steps)

        if "difficulty" in data:
            print_breakdown(data, per_model)

    print("\n" + "=" * 86)
    header = ("task", "model", "test score", "params", "depth", "train s")
    widths = (9, 18, 17, 9, 12, 8)
    print("".join(f"{h:<{w}}" for h, w in zip(header, widths)))
    for row in summary:
        print("".join(f"{v:<{w}}" for v, w in zip(row, widths)))


if __name__ == "__main__":
    main()
