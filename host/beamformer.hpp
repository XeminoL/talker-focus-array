#pragma once

#include <algorithm>
#include <cmath>
#include <memory>
#include <string>
#include <vector>

#include "delay_filter.hpp"
#include "geometry.hpp"

using Weights = std::vector<std::vector<double>>;

class Beamformer {
public:
    virtual ~Beamformer() = default;
    virtual Weights design(const Scene& scene) const = 0;
    virtual std::string name() const = 0;
};

inline std::vector<double> arrival_delays(const Scene& scene) {
    std::vector<double> distance;
    for (const Point& mic : scene.mics) distance.push_back((scene.target - mic).norm());
    double farthest = *std::max_element(distance.begin(), distance.end());
    std::vector<double> delay;
    for (double d : distance) delay.push_back((farthest - d) / scene.speed * scene.rate);
    return delay;
}

class DelayAndSum : public Beamformer {
public:
    DelayAndSum(std::unique_ptr<DelayFilter> filter, int length, double base_delay)
        : filter_(std::move(filter)), length_(length), base_delay_(base_delay) {}

    Weights design(const Scene& scene) const override {
        std::vector<double> delay = arrival_delays(scene);
        double count = static_cast<double>(scene.mics.size());
        Weights out;
        for (std::size_t m = 0; m < scene.mics.size(); ++m) {
            std::vector<double> taps = filter_->taps(base_delay_ + delay[m], length_);
            for (double& t : taps) t /= count;
            out.push_back(taps);
        }
        return out;
    }

    std::string name() const override { return "das-" + filter_->name(); }

private:
    std::unique_ptr<DelayFilter> filter_;
    int length_;
    double base_delay_;
};
