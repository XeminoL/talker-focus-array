#pragma once

#include <cmath>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Point {
    double x = 0, y = 0, z = 0;

    Point operator-(const Point& other) const { return {x - other.x, y - other.y, z - other.z}; }
    Point operator+(const Point& other) const { return {x + other.x, y + other.y, z + other.z}; }
    Point operator*(double scale) const { return {x * scale, y * scale, z * scale}; }
    double norm() const { return std::sqrt(x * x + y * y + z * z); }
};

struct Scene {
    std::vector<Point> mics;
    Point target;
    double rate = 16000.0;
    double speed = 343.0;
};

inline Scene read_scene(const std::string& path) {
    std::ifstream file(path);
    if (!file) throw std::runtime_error("cannot open " + path);
    Scene scene;
    std::string line;
    while (std::getline(file, line)) {
        std::istringstream words(line);
        std::string key;
        words >> key;
        if (key == "mic") {
            Point p;
            words >> p.x >> p.y >> p.z;
            scene.mics.push_back(p);
        } else if (key == "target") {
            words >> scene.target.x >> scene.target.y >> scene.target.z;
        } else if (key == "rate") {
            words >> scene.rate;
        } else if (key == "speed") {
            words >> scene.speed;
        }
    }
    if (scene.mics.empty()) throw std::runtime_error("no microphones in " + path);
    return scene;
}
