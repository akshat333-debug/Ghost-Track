// Path Finder: IMU-only 6-DoF trajectory under sensor degradation. Team Zero Drift.
// Usage: pathfinder <imu0/data.csv> <estimated_trajectory.txt>
// C++ port of research/baselines/eskf.py; tests/test_cpp_parity.py keeps the two identical.
// Reads the file twice and streams output, so memory does not grow with sequence length.
// shortcut: poses are written only for rows present in the input, upgrade after organizer answers Q6/Q7.
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#ifdef PF_NET  // built with the learned velocity measurement (L3); without it, classical ESKF only
#include "vel_net.hpp"
#endif

template <int R, int C> struct Mat {
    double a[R][C] = {};
    double* operator[](int i) { return a[i]; }
    const double* operator[](int i) const { return a[i]; }
};
using V3 = Mat<3, 1>;
using M3 = Mat<3, 3>;
using M15 = Mat<15, 15>;

template <int R, int K, int C> Mat<R, C> operator*(const Mat<R, K>& x, const Mat<K, C>& y) {
    Mat<R, C> o;
    for (int i = 0; i < R; i++)
        for (int k = 0; k < K; k++)
            for (int j = 0; j < C; j++) o[i][j] += x[i][k] * y[k][j];
    return o;
}
template <int R, int C> Mat<R, C> operator+(Mat<R, C> x, const Mat<R, C>& y) {
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) x[i][j] += y[i][j];
    return x;
}
template <int R, int C> Mat<R, C> operator-(Mat<R, C> x, const Mat<R, C>& y) {
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) x[i][j] -= y[i][j];
    return x;
}
template <int R, int C> Mat<R, C> operator*(double s, Mat<R, C> x) {
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) x[i][j] *= s;
    return x;
}
template <int R, int C> Mat<C, R> tr(const Mat<R, C>& x) {
    Mat<C, R> o;
    for (int i = 0; i < R; i++)
        for (int j = 0; j < C; j++) o[j][i] = x[i][j];
    return o;
}
template <int N> Mat<N, N> eye() {
    Mat<N, N> o;
    for (int i = 0; i < N; i++) o[i][i] = 1;
    return o;
}
template <int R, int C, int M, int N> void place(Mat<R, C>& x, int r, int c, const Mat<M, N>& y) {
    for (int i = 0; i < M; i++)
        for (int j = 0; j < N; j++) x[r + i][c + j] = y[i][j];
}
static V3 v3(double x, double y, double z) {
    V3 v;
    v[0][0] = x; v[1][0] = y; v[2][0] = z;
    return v;
}
static M3 skew(const V3& v) {
    M3 s;
    s[0][1] = -v[2][0]; s[0][2] = v[1][0];
    s[1][0] = v[2][0];  s[1][2] = -v[0][0];
    s[2][0] = -v[1][0]; s[2][1] = v[0][0];
    return s;
}
static double norm(const V3& v) { return std::sqrt(v[0][0] * v[0][0] + v[1][0] * v[1][0] + v[2][0] * v[2][0]); }
static M3 exp_so3(const V3& phi) {
    double a = norm(phi);
    M3 S = skew(phi);
    if (a < 1e-8) return eye<3>() + S;
    return eye<3>() + (std::sin(a) / a) * S + ((1 - std::cos(a)) / (a * a)) * (S * S);
}
static M3 inv3(const M3& m) {
    M3 o;
    double c0 = m[1][1] * m[2][2] - m[1][2] * m[2][1];
    double c1 = m[1][2] * m[2][0] - m[1][0] * m[2][2];
    double c2 = m[1][0] * m[2][1] - m[1][1] * m[2][0];
    double d = 1.0 / (m[0][0] * c0 + m[0][1] * c1 + m[0][2] * c2);
    o[0][0] = c0 * d; o[0][1] = (m[0][2] * m[2][1] - m[0][1] * m[2][2]) * d; o[0][2] = (m[0][1] * m[1][2] - m[0][2] * m[1][1]) * d;
    o[1][0] = c1 * d; o[1][1] = (m[0][0] * m[2][2] - m[0][2] * m[2][0]) * d; o[1][2] = (m[0][2] * m[1][0] - m[0][0] * m[1][2]) * d;
    o[2][0] = c2 * d; o[2][1] = (m[0][1] * m[2][0] - m[0][0] * m[2][1]) * d; o[2][2] = (m[0][0] * m[1][1] - m[0][1] * m[1][0]) * d;
    return o;
}

const double G = 9.81;
const int UPDATE_EVERY = 20, STATIC_WINDOW = 100;
const double GYRO_NOISE = 1.7e-4, ACCEL_NOISE = 2.0e-3, GYRO_WALK = 1.9e-5, ACCEL_WALK = 3.0e-3;
const double TILT_SIGMA = 4.0, POS_SIGMA = 15.0, STATIC_VEL_SIGMA = 0.1;
[[maybe_unused]] const double VEL_SIGMA = 1.5;  // replaced by the net in PF_NET builds
const double STATIC_RATIO = 3.0, BLIND_TAU = 1.0, BLIND_PULL_TAU = 1.0;
const int CENTROID_NODES = 200;

struct Filter {
    V3 p, v, bg, ba;
    M3 C = eye<3>();
    M15 P;
    Filter() {
        const double d[5] = {1e-3, 0.5, 0.05, 0.02, 0.2};
        for (int i = 0; i < 15; i++) P[i][i] = d[i / 3] * d[i / 3];
    }
    void propagate(const V3& wm, const V3& fm, double dt, double scale) {
        V3 w = wm - bg, f = fm - ba;
        V3 acc = (C * f) - v3(0, 0, G);
        M15 F = eye<15>();
        place(F, 0, 3, dt * eye<3>());
        place(F, 3, 6, (-dt) * (C * skew(f)));
        place(F, 3, 12, (-dt) * C);
        place(F, 6, 6, eye<3>() - dt * skew(w));
        place(F, 6, 9, (-dt) * eye<3>());
        P = F * P * tr(F);
        double q[4] = {ACCEL_NOISE * scale, GYRO_NOISE * scale, GYRO_WALK * scale, ACCEL_WALK * scale};
        for (int b = 1; b < 5; b++)
            for (int i = 0; i < 3; i++) P[3 * b + i][3 * b + i] += q[b - 1] * q[b - 1] * dt;
        p = p + dt * v + (0.5 * dt * dt) * acc;
        v = v + dt * acc;
        C = C * exp_so3(dt * w);
    }
    void coast(double dt, double decay) {
        p = p + dt * v;
        v = decay * v;
        M15 F = eye<15>();
        place(F, 0, 3, dt * eye<3>());
        P = F * P * tr(F);
        for (int i = 0; i < 3; i++) {
            P[3 + i][3 + i] += 1.0 * dt;
            P[6 + i][6 + i] += 0.3 * dt;
        }
    }
    void update(const V3& r, const Mat<3, 15>& H, double sigma) {
        const double s[3] = {sigma, sigma, sigma};
        update(r, H, s);
    }
    void update(const V3& r, const Mat<3, 15>& H, const double sigma[3]) {
        M3 Rn;
        for (int i = 0; i < 3; i++) Rn[i][i] = sigma[i] * sigma[i];
        Mat<15, 3> PHt = P * tr(H);
        Mat<15, 3> K = PHt * inv3(H * PHt + Rn);
        Mat<15, 1> dx = K * r;
        M15 I_KH = eye<15>() - K * H;
        P = I_KH * P * tr(I_KH) + K * Rn * tr(K);
        V3 dp, dv, dt, db, da;
        for (int i = 0; i < 3; i++) {
            dp[i][0] = dx[i][0]; dv[i][0] = dx[3 + i][0]; dt[i][0] = dx[6 + i][0];
            db[i][0] = dx[9 + i][0]; da[i][0] = dx[12 + i][0];
        }
        p = p + dp; v = v + dv; C = C * exp_so3(dt); bg = bg + db; ba = ba + da;
    }
    void update_tilt(const V3& f_mean, double sigma) {
        V3 up = tr(C) * v3(0, 0, G);
        Mat<3, 15> H;
        place(H, 0, 6, skew(up));
        place(H, 0, 12, eye<3>());
        update(f_mean - ba - up, H, sigma);
    }
    void update_velocity(double sigma) {
        Mat<3, 15> H;
        place(H, 0, 3, eye<3>());
        update((-1.0) * v, H, sigma);
    }
    void update_velocity(const V3& target, const double sigma[3]) {
        Mat<3, 15> H;
        place(H, 0, 3, eye<3>());
        update(target - v, H, sigma);
    }
    void update_position(double sigma) {
        Mat<3, 15> H;
        place(H, 0, 0, eye<3>());
        update((-1.0) * p, H, sigma);
    }
    void update_gyro_bias(const V3& w_mean, double sigma) {
        Mat<3, 15> H;
        place(H, 0, 9, eye<3>());
        update(w_mean - bg, H, sigma);
    }
};

// Noise inflation from first differences: motion is slow at 200 Hz, noise is not.
struct NoiseScale {
    double power = 0, out = 1, prev[3];
    bool seeded = false, first = true;
    double step(const double x[3], double nominal, double dt) {
        double e = 0;
        for (int i = 0; i < 3; i++) {
            double d = first ? 0.0 : x[i] - prev[i];
            if (!std::isnan(d)) e += d * d;
            prev[i] = x[i];
        }
        first = false;
        e /= 6;
        if (e != 0) {
            power = seeded ? power + (e - power) / 200 : e;
            seeded = true;
            out = std::max(1.0, std::sqrt(power * dt) / nominal);
        }
        return out;
    }
};

// Static when window spread is indistinguishable from sensor noise.
static bool quiet(const double x[][3], int n, double ratio) {
    double var = 0, hf = 0;
    for (int a = 0; a < 3; a++) {
        double m = 0, v = 0, d = 0;
        for (int i = 0; i < n; i++) m += x[i][a];
        m /= n;
        for (int i = 0; i < n; i++) v += (x[i][a] - m) * (x[i][a] - m);
        for (int i = 1; i < n; i++) d += (x[i][a] - x[i - 1][a]) * (x[i][a] - x[i - 1][a]);
        var += v / n;
        hf += d / (n - 1);
    }
    return var <= ratio * hf / 2;
}

static V3 mean(const double x[][3], int from, int n) {
    double s[3] = {0, 0, 0};
    for (int i = from; i < n; i++)
        for (int a = 0; a < 3; a++) s[a] += x[i][a];
    int c = n - from;
    return v3(s[0] / c, s[1] / c, s[2] / c);
}

// Returns false for a comment, header or row without a timestamp. Unparsable values become NaN.
static bool parse_row(char* line, int64_t& t, double v[6]) {
    if (line[0] == '#') return false;
    char* end;
    t = std::strtoll(line, &end, 10);
    if (end == line || *end != ',') return false;
    const char* p = end;
    for (int i = 0; i < 6; i++) {
        v[i] = NAN;
        if (p && *p == ',') {
            char* e;
            double d = std::strtod(p + 1, &e);
            if (e != p + 1) v[i] = d;
            p = std::strchr(p + 1, ',');
        }
    }
    return true;
}

static bool row_good(const double v[6]) {
    for (int i = 0; i < 6; i++)
        if (std::isnan(v[i])) return false;
    return true;
}

static M3 align_to_up(V3 a) {
    a = (1.0 / norm(a)) * a;
    double c = a[2][0];
    M3 out = eye<3>();
    if (c < -1 + 1e-9) {
        out[1][1] = -1;
        out[2][2] = -1;
        return out;
    }
    M3 S = skew(v3(a[1][0], -a[0][0], 0.0));
    return eye<3>() + S + (1.0 / (1 + c)) * (S * S);
}

static void write_pose(FILE* f, int64_t t, const Filter& s) {
    const M3& R = s.C;
    double q[4], tr_ = R[0][0] + R[1][1] + R[2][2];
    if (tr_ > 0) {
        double w = std::sqrt(1 + tr_) * 2;
        q[0] = (R[2][1] - R[1][2]) / w; q[1] = (R[0][2] - R[2][0]) / w;
        q[2] = (R[1][0] - R[0][1]) / w; q[3] = w / 4;
    } else {
        int i = (R[1][1] > R[0][0]) ? 1 : 0;
        if (R[2][2] > R[i][i]) i = 2;
        int j = (i + 1) % 3, k = (i + 2) % 3;
        double w = std::sqrt(1 + R[i][i] - R[j][j] - R[k][k]) * 2;
        q[i] = w / 4; q[j] = (R[j][i] + R[i][j]) / w;
        q[k] = (R[k][i] + R[i][k]) / w; q[3] = (R[k][j] - R[j][k]) / w;
    }
    double n = std::sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3]);
    std::fprintf(f, "%lld.%09lld %.6f %.6f %.6f %.9f %.9f %.9f %.9f\n",
                 (long long)(t / 1000000000), (long long)(t % 1000000000), s.p[0][0], s.p[1][0], s.p[2][0],
                 q[0] / n, q[1] / n, q[2] / n, q[3] / n);
}

int main(int argc, char** argv) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: %s <imu.csv> <estimated_trajectory.txt>\n", argv[0]);
        return 2;
    }
    FILE* in = std::fopen(argv[1], "r");
    if (!in) {
        std::perror(argv[1]);
        return 1;
    }
    char line[512];
    int64_t t, t0 = 0, t_first_good = -1;
    double v[6], a0[3] = {0, 0, 0}, prev_T = 0;
    long n = 0, last_good = -1, a0_count = 0;
    std::vector<double> diffs;
    diffs.reserve(10000);
    while (std::fgets(line, sizeof line, in)) {
        if (!parse_row(line, t, v)) continue;
        if (n == 0) t0 = t;
        double T = (t - t0) * 1e-9;
        if (n > 0 && diffs.size() < 10000) diffs.push_back(T - prev_T);
        prev_T = T;
        if (row_good(v)) {
            if (t_first_good < 0) t_first_good = t;
            last_good = n;
            if ((t - t0) * 1e-9 < (t_first_good - t0) * 1e-9 + 1.0) {
                for (int i = 0; i < 3; i++) a0[i] += v[3 + i];
                a0_count++;
            }
        }
        n++;
    }
    if (last_good < 0) {
        std::fprintf(stderr, "no valid IMU rows in %s\n", argv[1]);
        return 1;
    }
    double median_dt = 0.005;
    if (!diffs.empty()) {
        std::sort(diffs.begin(), diffs.end());
        size_t m = diffs.size() / 2;
        median_dt = diffs.size() % 2 ? diffs[m] : (diffs[m - 1] + diffs[m]) / 2;
    }
    std::vector<double>().swap(diffs);

    FILE* out = std::fopen(argv[2], "w");
    if (!out) {
        std::perror(argv[2]);
        return 1;
    }
    Filter s;
    s.C = align_to_up((1.0 / a0_count) * v3(a0[0], a0[1], a0[2]));
    NoiseScale ns_g, ns_a;
    const int W = STATIC_WINDOW + 1;
    double ring_g[W][3], ring_a[W][3], win_g[W][3], win_a[W][3];
    long good_run = 0, i = 0;
    double T_prev = 0, T_last_good = 0;
    double recent[CENTROID_NODES][3];
    int recent_n = 0, recent_at = 0;
    bool blind_started = false;
#ifdef PF_NET
    static double ring_imu[velnet::WINDOW][6];
    static M3 ring_C[velnet::WINDOW];
    static float net_x[velnet::IN_CHANNELS * velnet::WINDOW];
    double f_sum[3] = {0, 0, 0};
    ring_C[0] = s.C;
#endif
    V3 blind_p0, blind_v0, blind_centre;

    std::rewind(in);
    while (std::fgets(line, sizeof line, in)) {
        if (!parse_row(line, t, v)) continue;
        bool good = row_good(v);
        double T = (t - t0) * 1e-9;
        double scale = std::max(ns_g.step(v, GYRO_NOISE, median_dt), ns_a.step(v + 3, ACCEL_NOISE, median_dt));
        good_run = good ? good_run + 1 : 0;
        std::memcpy(ring_g[i % W], v, sizeof ring_g[0]);
        std::memcpy(ring_a[i % W], v + 3, sizeof ring_a[0]);
        if (i > 0) {
            double dt = T - T_prev;
            if (good) {
                s.propagate(v3(v[0], v[1], v[2]), v3(v[3], v[4], v[5]), dt, scale);
#ifdef PF_NET
                for (int a = 0; a < 3; a++) f_sum[a] += v[3 + a];
#endif
            } else {
                s.coast(dt, i > last_good ? std::exp(-dt / BLIND_TAU) : 1.0);
                if (i > last_good) {
                    if (!blind_started) {
                        blind_started = true;
                        blind_p0 = s.p - dt * s.v;
                        blind_v0 = s.v;
                        blind_centre = recent_n ? mean(recent, 0, recent_n) : s.p;
                    }
                    double tb = T - T_last_good, pull = 1 - std::exp(-tb / BLIND_PULL_TAU);
                    s.p = (1 - pull) * (blind_p0 + (BLIND_TAU * (1 - std::exp(-tb / BLIND_TAU))) * blind_v0) + pull * blind_centre;
                }
            }
            if (good && i % UPDATE_EVERY == 0) {
                for (int a = 0; a < 3; a++) recent[recent_at][a] = s.p[a][0];
                recent_at = (recent_at + 1) % CENTROID_NODES;
                recent_n = std::min(recent_n + 1, CENTROID_NODES);
            }
            if (good && i >= STATIC_WINDOW && i % UPDATE_EVERY == 0 && good_run >= W) {
                for (int k = 0; k < W; k++) {
                    int idx = (i + 1 + k) % W;
                    std::memcpy(win_g[k], ring_g[idx], sizeof win_g[0]);
                    std::memcpy(win_a[k], ring_a[idx], sizeof win_a[0]);
                }
                if (quiet(win_g, W, STATIC_RATIO) && quiet(win_a, W, STATIC_RATIO)) {
                    s.update_velocity(STATIC_VEL_SIGMA);
                    s.update_tilt(mean(win_a, 0, W), 0.05 * std::sqrt(scale));
                    s.update_gyro_bias(mean(win_g, 0, W),
                                       GYRO_NOISE * scale * std::sqrt(1 / median_dt / STATIC_WINDOW));
                } else {
                    s.update_tilt(mean(win_a, W - UPDATE_EVERY, W), TILT_SIGMA);
#ifndef PF_NET
                    s.update_velocity(VEL_SIGMA);
#endif
                }
                s.update_position(POS_SIGMA);
            }
#ifdef PF_NET
            std::memcpy(ring_imu[i % velnet::WINDOW], v, sizeof ring_imu[0]);
            if (good && i >= velnet::WINDOW && i % UPDATE_EVERY == 0) {
                ring_C[i % velnet::WINDOW] = s.C;
                double nf = std::sqrt(f_sum[0] * f_sum[0] + f_sum[1] * f_sum[1] + f_sum[2] * f_sum[2]);
                V3 axis = v3(f_sum[0] / nf, f_sum[1] / nf, f_sum[2] / nf);
                for (int k = 0; k < velnet::WINDOW; k++) {
                    int idx = (i + 1 + k) % velnet::WINDOW;
                    const double* r = ring_imu[idx];
                    bool ok = row_good(r);
                    V3 gw = ring_C[idx] * (ok ? v3(r[0], r[1], r[2]) : V3());
                    V3 aw = ring_C[idx] * (ok ? v3(r[3], r[4], r[5]) : V3());
                    if (ok) aw[2][0] -= G;
                    V3 tw = ring_C[idx] * axis;
                    for (int c = 0; c < 3; c++) {
                        net_x[c * velnet::WINDOW + k] = (float)(gw[c][0] / 3.0);
                        net_x[(3 + c) * velnet::WINDOW + k] = (float)(aw[c][0] / 5.0);
                        net_x[(7 + c) * velnet::WINDOW + k] = (float)tw[c][0];
                    }
                    net_x[6 * velnet::WINDOW + k] = ok ? 1.0f : 0.0f;
                }
                double mu[3], sigma[3];
                velnet::forward(net_x, mu, sigma);
                s.update_velocity(v3(mu[0], mu[1], mu[2]), sigma);
            }
            ring_C[i % velnet::WINDOW] = s.C;
#endif
        }
        write_pose(out, t, s);
        if (good) T_last_good = T;
        T_prev = T;
        i++;
    }
    if (std::fclose(out) != 0) {
        std::perror(argv[2]);
        return 1;
    }
    std::fclose(in);
    return 0;
}
