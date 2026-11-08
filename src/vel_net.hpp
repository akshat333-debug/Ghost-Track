// Forward pass of the velocity net (research/nets/vel_net.py). No allocation; single thread.
#pragma once
#include <algorithm>
#include <cmath>

#include "weights.hpp"

namespace velnet {
const int WINDOW = 200, IN_CHANNELS = 10;

// x and out are (channels, time) in row-major order; kernel 5, stride 2, padding 2, then ReLU.
inline int conv(const float* x, int ci, int len, const float* w, const float* b, int co, float* out) {
    int n = (len + 4 - 5) / 2 + 1;
    for (int o = 0; o < co; o++) {
        float* y = out + o * n;
        for (int t = 0; t < n; t++) {
            float s = b[o];
            int start = t * 2 - 2;
            for (int c = 0; c < ci; c++) {
                const float* k = w + (o * ci + c) * 5;
                const float* xc = x + c * len;
                for (int j = 0; j < 5; j++) {
                    int at = start + j;
                    if (at >= 0 && at < len) s += k[j] * xc[at];
                }
            }
            y[t] = std::max(s, 0.0f);
        }
    }
    return n;
}

inline void linear(const float* x, int in, const float* w, const float* b, int out_n, float* out) {
    for (int o = 0; o < out_n; o++) {
        float s = b[o];
        for (int i = 0; i < in; i++) s += w[o * in + i] * x[i];
        out[o] = s;
    }
}

// x: IN_CHANNELS * WINDOW floats. Writes mean velocity[3] and standard deviation[3].
inline void forward(const float* x, double mu[3], double sigma[3]) {
    static float a0[16 * 100], a1[32 * 50], a2[48 * 25], a3[64 * 13], a4[64 * 7], a5[64 * 4], h[64], o[6];
    int n = conv(x, IN_CHANNELS, WINDOW, C0_weight, C0_bias, 16, a0);
    n = conv(a0, 16, n, C1_weight, C1_bias, 32, a1);
    n = conv(a1, 32, n, C2_weight, C2_bias, 48, a2);
    n = conv(a2, 48, n, C3_weight, C3_bias, 64, a3);
    n = conv(a3, 64, n, C4_weight, C4_bias, 64, a4);
    n = conv(a4, 64, n, C5_weight, C5_bias, 64, a5);
    linear(a5, 64 * 4, L0_weight, L0_bias, 64, h);
    for (float& v : h) v = std::max(v, 0.0f);
    linear(h, 64, L1_weight, L1_bias, 6, o);
    for (int i = 0; i < 3; i++) {
        mu[i] = o[i];
        sigma[i] = std::exp(0.5f * std::min(std::max(o[3 + i], -8.0f), 4.0f));
    }
}
}  // namespace velnet
