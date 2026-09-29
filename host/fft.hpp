#pragma once

#include <cmath>
#include <complex>
#include <stdexcept>
#include <vector>

inline std::vector<std::complex<double>> fft(const std::vector<std::complex<double>>& x, bool inverse = false) {
    std::size_t n = x.size();
    if (n == 1) return x;
    if (n % 2 != 0) throw std::invalid_argument("fft size must be a power of two");
    std::vector<std::complex<double>> even(n / 2), odd(n / 2);
    for (std::size_t i = 0; i < n / 2; ++i) {
        even[i] = x[2 * i];
        odd[i] = x[2 * i + 1];
    }
    auto e = fft(even, inverse);
    auto o = fft(odd, inverse);
    double sign = inverse ? 1.0 : -1.0;
    std::vector<std::complex<double>> out(n);
    for (std::size_t k = 0; k < n / 2; ++k) {
        auto twiddle = std::polar(1.0, sign * 2.0 * M_PI * k / n) * o[k];
        out[k] = e[k] + twiddle;
        out[k + n / 2] = e[k] - twiddle;
    }
    return out;
}

inline std::vector<std::complex<double>> ifft(const std::vector<std::complex<double>>& x) {
    auto out = fft(x, true);
    for (auto& v : out) v /= static_cast<double>(x.size());
    return out;
}
