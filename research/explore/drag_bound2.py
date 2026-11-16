"""Feasibility bound for drag odometry on clean train data, ground-truth attitude, IMU-only flight gate."""
import sys
import numpy as np
from evo.core import geometry
from scipy.spatial.transform import Rotation as R, Slerp
from research.io_euroc import load_seq
from research.split import SPLITS
K, NODE_S = 0.177, 0.2

def roll(x, n):
    return np.convolve(x, np.ones(n) / n, "same")

def rollv(x, n):
    return np.c_[[roll(x[:, i], n) for i in range(x.shape[1])]].T

def nodes(name):
    t_ns, gyro, accel, (gt_t, gt_p, gt_q) = load_seq(name)
    T, Tg = (t_ns - gt_t[0]) * 1e-9, (gt_t - gt_t[0]) * 1e-9
    n = int(round(NODE_S / np.median(np.diff(T)))); m = len(T) // n
    f = accel[:m*n].reshape(m, n, 3).mean(axis=1); tt = T[:m*n].reshape(m, n).mean(axis=1)
    rot = Slerp(Tg, R.from_quat(gt_q))(tt)
    gt = np.c_[[np.interp(tt, Tg, gt_p[:, i]) for i in range(3)]].T
    return tt, f, rot, gt

def flight_gate(f, gate, win_s=15.0):
    W = int(win_s / NODE_S)
    fly = np.ones(len(f), bool)
    for _ in range(3):
        up = f[fly].mean(axis=0); up /= np.linalg.norm(up)
        lat = f - np.outer(f @ up, up)
        dev = lat - rollv(lat, W)
        fly = np.sqrt(roll(np.sum(dev ** 2, axis=1), W)) < gate
        if fly.sum() < 50:
            return np.zeros(len(f), bool), up
    return fly, up

def run(name, knots_s=30.0, smooth_s=1.0, gate=0.25, ridge=1e-6):
    tt, f, rot, gt = nodes(name)
    m = len(tt)
    fly, up = flight_gate(f, gate)
    e1 = np.cross(up, [1.0,0,0] if abs(up[0])<0.9 else [0,1.0,0]); e1/=np.linalg.norm(e1)
    E = np.c_[e1, np.cross(up, e1)]
    lat = rollv(f - np.outer(f@up, up), max(1,int(smooth_s/NODE_S)))
    g = fly[:,None].astype(float)
    v0 = -rot.apply(lat)/K*g
    knots = np.arange(0, tt[-1]+knots_s, knots_s)
    H = np.maximum(0, 1-np.abs(tt[:,None]-knots[None])/knots_s)
    RE = rot.as_matrix()@E/K*g[:,:,None]
    J = (RE[:,:,None,:]*H[:,None,:,None]).reshape(m,3,-1)
    p0 = np.cumsum(v0,axis=0)*NODE_S; B=np.cumsum(J,axis=0)*NODE_S
    p0c,Bc = p0-p0.mean(0), B-B.mean(0)
    A = np.einsum("mik,mil->kl",Bc,Bc)+ridge*np.eye(B.shape[2])
    beta = np.linalg.solve(A, -np.einsum("mik,mi->k",Bc,p0c))
    p = p0+B@beta; v = v0+J@beta
    vgt = np.gradient(gt, tt, axis=0)
    out = {"null": np.sqrt(np.mean(np.sum((gt-gt.mean(0))**2,axis=1))), "fly": fly.mean()}
    try:
        ra,tr,_ = geometry.umeyama_alignment(p.T, gt.T); out["ate"]=np.sqrt(np.mean(np.sum(((ra@p.T).T+tr-gt)**2,axis=1)))
    except Exception:
        out["ate"]=float("nan")
    if fly.any():
        out["verr"]=np.sqrt(np.mean(np.sum((v-vgt)[fly]**2,axis=1))); out["vzero"]=np.sqrt(np.mean(np.sum(vgt[fly]**2,axis=1)))
        out["verr_h"]=np.sqrt(np.mean(np.sum((v-vgt)[fly][:,:2]**2,axis=1))); out["vzero_h"]=np.sqrt(np.mean(np.sum(vgt[fly][:,:2]**2,axis=1)))
    return out

if __name__ == "__main__":
    for name in SPLITS["train"]:
        rs = [run(name, kn) for kn in (1e9, 60.0, 30.0, 15.0)]
        r = rs[2]
        print(f"{name}: null {r['null']:.2f} fly {r['fly']:.2f} | ATE const/60/30/15: {' '.join('%.2f'%x['ate'] for x in rs)}"
              + (f" | horiz vel rmse {r['verr_h']:.2f} vs zero {r['vzero_h']:.2f}; 3D {r['verr']:.2f} vs {r['vzero']:.2f}" if 'verr' in r else ""))
