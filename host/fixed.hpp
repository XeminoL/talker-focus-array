#pragma once

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

template <int Bits>
class Fixed {
public:
    static constexpr std::int64_t max_raw = (std::int64_t{1} << (Bits - 1)) - 1;
    static constexpr std::int64_t min_raw = -(std::int64_t{1} << (Bits - 1));

    Fixed() = default;
    Fixed(double value, int fraction) {
        double scaled = std::round(value * std::ldexp(1.0, fraction));
        if (scaled > max_raw || scaled < min_raw) throw std::range_error("value does not fit");
        raw_ = static_cast<std::int64_t>(scaled);
    }

    std::int64_t raw() const { return raw_; }
    std::string hex() const {
        char text[32];
        std::uint64_t mask = (std::uint64_t{1} << Bits) - 1;
        std::snprintf(text, sizeof text, "%0*llx", (Bits + 3) / 4, static_cast<unsigned long long>(raw_ & mask));
        return text;
    }

private:
    std::int64_t raw_ = 0;
};

template <int Bits>
int fraction_bits_for(const std::vector<std::vector<double>>& weights, int limit) {
    double peak = 0.0;
    for (const auto& row : weights)
        for (double w : row) peak = std::fmax(peak, std::fabs(w));
    int fraction = 0;
    while (fraction < limit && peak * std::ldexp(1.0, fraction + 1) < static_cast<double>(Fixed<Bits>::max_raw)) ++fraction;
    return fraction;
}

template <int Bits>
void write_weights(const std::vector<std::vector<double>>& weights, int fraction, const std::string& prefix) {
    std::ofstream hex(prefix + ".hex");
    for (const auto& row : weights)
        for (double w : row) hex << Fixed<Bits>(w, fraction).hex() << "\n";
    std::ofstream shift(prefix + ".shift");
    shift << fraction << "\n";
    if (!hex || !shift) throw std::runtime_error("cannot write " + prefix);
}
