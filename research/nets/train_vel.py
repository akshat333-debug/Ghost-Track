#!/usr/bin/env python3
"""Trains the velocity net with an environment left out (D-007).

python -m research.nets.train_vel --fold 0 --epochs 60 --out vel_fold0.pt
--fold final trains on train+val for the epoch count CV chose. Works unchanged on Colab or Kaggle.
"""
import argparse

import numpy as np
import torch
import torch.nn.functional as nnf

from research.nets.data import Sequence, make_batch
from research.nets.vel_net import VelNet, param_count
from research.split import FOLDS, SPLITS

BATCH, STEPS = 256, 400
EVAL_BATCHES = 40


def device():
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def nll(mu, logvar, y):
    return (0.5 * ((mu - y) ** 2 * torch.exp(-logvar) + logvar)).mean()


@torch.no_grad()
def evaluate(model, seqs, dev, seed=1234):
    """Fixed corruption seed, so epochs are comparable. Returns RMSE, zero-predictor RMSE, 1-sigma coverage."""
    rng = np.random.default_rng(seed)
    se, zero, inside, count = 0.0, 0.0, 0.0, 0
    model.eval()
    for _ in range(EVAL_BATCHES):
        x, y = make_batch(seqs, BATCH, rng)
        x, y = torch.from_numpy(x).to(dev), torch.from_numpy(y).to(dev)
        mu, logvar = model(x)
        err = mu - y
        se += (err**2).sum().item()
        zero += (y**2).sum().item()
        inside += (err.abs() < torch.exp(0.5 * logvar)).float().sum().item()
        count += y.numel()
    return np.sqrt(se / count), np.sqrt(zero / count), inside / count


def train(train_seqs, test_seqs, epochs, out=None, seed=0, warmup=None):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    dev = device()
    model = VelNet().to(dev)
    assert param_count(model) <= 100_000, "D-007 capacity limit"
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs * STEPS)
    warmup = epochs // 4 if warmup is None else warmup
    best = (float("inf"), -1)
    history = []
    for ep in range(epochs):
        model.train()
        for _ in range(STEPS):
            x, y = make_batch(train_seqs, BATCH, rng)
            x, y = torch.from_numpy(x).to(dev), torch.from_numpy(y).to(dev)
            mu, logvar = model(x)
            loss = nnf.mse_loss(mu, y) if ep < warmup else nll(mu, logvar, y)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            opt.step()
            sched.step()
        fit = evaluate(model, train_seqs, dev)
        res = evaluate(model, test_seqs, dev) if test_seqs else (float("nan"),) * 3
        history.append((ep, *fit, *res))
        print(f"ep {ep} train_rmse {fit[0]:.3f} test_rmse {res[0]:.3f} test_zero {res[1]:.3f} coverage {res[2]:.2f}",
              flush=True)
        if test_seqs and ep >= warmup and res[0] < best[0]:  # warmup epochs have no trained uncertainty
            best = (res[0], ep)
            if out:
                torch.save(model.state_dict(), out)
    if out and not test_seqs:
        torch.save(model.state_dict(), out)
    return model, best, history


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fold", required=True)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.fold == "final":
        tr, te = SPLITS["train"] + SPLITS["val"], []
    else:
        te = FOLDS[int(a.fold)]
        tr = [s for s in SPLITS["train"] if s not in te]
    print("train", tr, "test", te, "device", device(), flush=True)
    _, best, _ = train([Sequence(s) for s in tr], [Sequence(s) for s in te], a.epochs, a.out, a.seed)
    print("BEST", best)
