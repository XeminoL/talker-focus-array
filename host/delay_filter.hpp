#pragma once

#include <cmath>
#include <memory>
#include <string>
#include <vector>

class DelayFilter {
public:
    virtual ~DelayFilter() = default;
    virtual std::vector<double> taps(double delay, int length) const = 0;
    virtual std::string name() const = 0;
};

class LagrangeDelay : public DelayFilter {
public:
    explicit LagrangeDelay(int order) : order_(order) {}

    std::vector<double> taps(double delay, int length) const override {
        std::vector<double> out(length, 0.0);
        int first = static_cast<int>(std::floor(delay)) - order_ / 2;
        if (first < 0) first = 0;
        if (first + order_ >= length) first = length - 1 - order_;
        double local = delay - first;
        for (int k = 0; k <= order_; ++k) {
            double value = 1.0;
            for (int i = 0; i <= order_; ++i)
                if (i != k) value *= (local - i) / static_cast<double>(k - i);
            out[first + k] = value;
        }
        return out;
    }

    std::string name() const override { return "lagrange" + std::to_string(order_); }

private:
    int order_;
};

class SincDelay : public DelayFilter {
public:
    explicit SincDelay(int half_width) : half_width_(half_width) {}

    std::vector<double> taps(double delay, int length) const override {
        std::vector<double> out(length, 0.0);
        for (int n = 0; n < length; ++n) {
            double t = n - delay;
            if (std::fabs(t) > half_width_) continue;
            double sinc = t == 0.0 ? 1.0 : std::sin(M_PI * t) / (M_PI * t);
            double window = 0.5 + 0.5 * std::cos(M_PI * t / half_width_);
            out[n] = sinc * window;
        }
        return out;
    }

    std::string name() const override { return "sinc" + std::to_string(half_width_); }

private:
    int half_width_;
};

inline std::unique_ptr<DelayFilter> make_delay_filter(const std::string& kind) {
    if (kind == "lagrange") return std::make_unique<LagrangeDelay>(7);
    return std::make_unique<SincDelay>(8);
}
