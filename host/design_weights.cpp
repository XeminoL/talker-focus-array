#include <cstdio>
#include <exception>
#include <memory>
#include <string>

#include "beamformer.hpp"
#include "fixed.hpp"
#include "mpdr.hpp"

constexpr int COEF_BITS = 18;
constexpr int FILTER_LENGTH = 64;
constexpr double BASE_DELAY = 10.0;
constexpr int FRACTION_LIMIT = 30;
constexpr int DESIGN_SIZE = 128;

std::unique_ptr<Beamformer> make_beamformer(const std::string& mode, const Scene& scene, int argc, char** argv) {
    if (mode == "das-sinc") return std::make_unique<DelayAndSum>(make_delay_filter("sinc"), FILTER_LENGTH, BASE_DELAY);
    if (mode == "das-lagrange") return std::make_unique<DelayAndSum>(make_delay_filter("lagrange"), FILTER_LENGTH, BASE_DELAY);
    if (mode == "mpdr") {
        if (argc < 6) throw std::invalid_argument("mpdr needs <recording.bin> <loading> [taps]");
        int taps = argc == 7 ? std::stoi(argv[6]) : FILTER_LENGTH;
        int size = DESIGN_SIZE;
        while (size < 2 * taps) size *= 2;
        return std::make_unique<MinimumPower>(read_recording(argv[4], scene.mics.size()), taps, size, std::stod(argv[5]));
    }
    throw std::invalid_argument("unknown mode " + mode);
}

int main(int argc, char** argv) {
    if (argc < 4 || argc == 5 || argc > 7) {
        std::fprintf(stderr, "usage: design_weights <das-sinc|das-lagrange|mpdr> <scene.txt> <out prefix> [recording.bin loading [taps]]\n");
        return 2;
    }
    try {
        Scene scene = read_scene(argv[2]);
        auto beamformer = make_beamformer(argv[1], scene, argc, argv);
        Weights weights = beamformer->design(scene);
        int fraction = fraction_bits_for<COEF_BITS>(weights, FRACTION_LIMIT);
        write_weights<COEF_BITS>(weights, fraction, argv[3]);
        std::printf("%s mics %zu taps %d fraction %d\n", beamformer->name().c_str(), weights.size(), FILTER_LENGTH, fraction);
    } catch (const std::exception& error) {
        std::fprintf(stderr, "error: %s\n", error.what());
        return 1;
    }
    return 0;
}
