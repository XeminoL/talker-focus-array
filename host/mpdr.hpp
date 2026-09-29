#pragma once

#include <cmath>
#include <cstdint>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

#include "beamformer.hpp"
#include "fft.hpp"
#include "linalg.hpp"

using Recording = std::vector<std::vector<double>>;

inline Recording read_recording(const std::string& path, std::size_t channels) {
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) throw std::runtime_error("cannot open " + path);
    std::size_t bytes = static_cast<std::size_t>(file.tellg());
    std::size_t samples = bytes / sizeof(std::int32_t) / channels;
    file.seekg(0);
    std::vector<std::int32_t> raw(samples * channels);
    file.read(reinterpret_cast<char*>(raw.data()), static_cast<std::streamsize>(raw.size() * sizeof(std::int32_t)));
    Recording out(channels, std::vector<double>(samples));
    for (std::size_t c = 0; c < channels; ++c)
        for (std::size_t n = 0; n < samples; ++n) out[c][n] = raw[c * samples + n];
    return out;
}

class MinimumPower : public Beamformer {
public:
    MinimumPower(Recording recording, int length, int design_size, double loading)
        : recording_(std::move(recording)), length_(length), design_size_(design_size), loading_(loading) {}

    Weights design(const Scene& scene) const override {
        std::size_t mics = scene.mics.size();
        std::size_t bins = static_cast<std::size_t>(design_size_ / 2 + 1);
        std::vector<Matrix<Complex>> covariance = estimate_covariance(mics, bins);
        std::vector<double> distance;
        for (const Point& mic : scene.mics) distance.push_back((scene.target - mic).norm());
        double nearest = distance[0], farthest = distance[0];
        for (double d : distance) {
            nearest = std::fmin(nearest, d);
            farthest = std::fmax(farthest, d);
        }
        double spread = (farthest - nearest) / scene.speed * scene.rate;
        double half = (length_ - spread) / 2.0;
        if (half < 4.0) throw std::runtime_error("filter too short for the array delay spread");
        double centre = half + spread;

        std::vector<std::vector<Complex>> response(mics, std::vector<Complex>(design_size_));
        for (std::size_t k = 0; k < bins; ++k) {
            double omega = 2.0 * M_PI * static_cast<double>(k) / design_size_;
            std::vector<Complex> steer(mics);
            for (std::size_t m = 0; m < mics; ++m) {
                double delay = (distance[m] - nearest) / scene.speed * scene.rate;
                steer[m] = std::polar(nearest / distance[m], -omega * delay);
            }
            Matrix<Complex> r = covariance[k];
            double load = loading_ * r.trace().real() / static_cast<double>(mics);
            for (std::size_t m = 0; m < mics; ++m) r(m, m) += load;
            std::vector<Complex> x = cholesky_solve(cholesky(r), steer);
            Complex gain = inner(steer, x);
            Complex shift = std::polar(1.0, -omega * centre);
            for (std::size_t m = 0; m < mics; ++m) {
                Complex h = std::conj(x[m] / gain) * shift;
                if (k == 0 || k == bins - 1) h = h.real();
                response[m][k] = h;
                if (k != 0 && k != bins - 1) response[m][design_size_ - k] = std::conj(h);
            }
        }

        Weights out;
        for (std::size_t m = 0; m < mics; ++m) {
            std::vector<Complex> impulse = ifft(response[m]);
            std::vector<double> taps(length_);
            double peak = centre - (distance[m] - nearest) / scene.speed * scene.rate;
            for (int n = 0; n < length_; ++n) {
                double t = (n - peak) / half;
                double window = std::fabs(t) < 1.0 ? 0.5 + 0.5 * std::cos(M_PI * t) : 0.0;
                taps[n] = impulse[static_cast<std::size_t>(n)].real() * window;
            }
            out.push_back(taps);
        }
        return out;
    }

    std::string name() const override { return "mpdr"; }

private:
    std::vector<Matrix<Complex>> estimate_covariance(std::size_t mics, std::size_t bins) const {
        std::vector<Matrix<Complex>> covariance(bins, Matrix<Complex>(mics, mics));
        std::size_t samples = recording_[0].size();
        std::size_t hop = static_cast<std::size_t>(design_size_ / 2);
        std::size_t frames = 0;
        std::vector<double> window(design_size_);
        for (int n = 0; n < design_size_; ++n) window[n] = 0.5 - 0.5 * std::cos(2.0 * M_PI * n / design_size_);
        std::vector<std::vector<Complex>> spectrum(mics);
        for (std::size_t start = 0; start + design_size_ <= samples; start += hop) {
            for (std::size_t m = 0; m < mics; ++m) {
                std::vector<Complex> frame(design_size_);
                for (int n = 0; n < design_size_; ++n) frame[n] = recording_[m][start + n] * window[n];
                spectrum[m] = fft(frame);
            }
            for (std::size_t k = 0; k < bins; ++k)
                for (std::size_t i = 0; i < mics; ++i)
                    for (std::size_t j = 0; j < mics; ++j) covariance[k](i, j) += spectrum[i][k] * std::conj(spectrum[j][k]);
            ++frames;
        }
        if (frames == 0) throw std::runtime_error("recording shorter than one frame");
        for (auto& c : covariance) c = c * (1.0 / static_cast<double>(frames));
        return covariance;
    }

    Recording recording_;
    int length_;
    int design_size_;
    double loading_;
};
