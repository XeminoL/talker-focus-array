#pragma once

#include <cmath>
#include <complex>
#include <stdexcept>
#include <vector>

using Complex = std::complex<double>;

template <typename T>
class Matrix {
public:
    Matrix() = default;
    Matrix(std::size_t rows, std::size_t cols) : rows_(rows), cols_(cols), data_(rows * cols) {}

    T& operator()(std::size_t r, std::size_t c) { return data_[r * cols_ + c]; }
    const T& operator()(std::size_t r, std::size_t c) const { return data_[r * cols_ + c]; }

    Matrix& operator+=(const Matrix& other) {
        for (std::size_t i = 0; i < data_.size(); ++i) data_[i] += other.data_[i];
        return *this;
    }

    Matrix operator*(double scale) const {
        Matrix out = *this;
        for (T& v : out.data_) v *= scale;
        return out;
    }

    std::size_t rows() const { return rows_; }
    std::size_t cols() const { return cols_; }

    T trace() const {
        T sum{};
        for (std::size_t i = 0; i < rows_; ++i) sum += (*this)(i, i);
        return sum;
    }

private:
    std::size_t rows_ = 0, cols_ = 0;
    std::vector<T> data_;
};

inline Matrix<Complex> cholesky(const Matrix<Complex>& a) {
    std::size_t n = a.rows();
    Matrix<Complex> l(n, n);
    for (std::size_t j = 0; j < n; ++j) {
        double diagonal = a(j, j).real();
        for (std::size_t k = 0; k < j; ++k) diagonal -= std::norm(l(j, k));
        if (diagonal <= 0.0) throw std::domain_error("matrix is not positive definite");
        l(j, j) = std::sqrt(diagonal);
        for (std::size_t i = j + 1; i < n; ++i) {
            Complex sum = a(i, j);
            for (std::size_t k = 0; k < j; ++k) sum -= l(i, k) * std::conj(l(j, k));
            l(i, j) = sum / l(j, j).real();
        }
    }
    return l;
}

inline std::vector<Complex> cholesky_solve(const Matrix<Complex>& l, const std::vector<Complex>& b) {
    std::size_t n = l.rows();
    std::vector<Complex> y(n), x(n);
    for (std::size_t i = 0; i < n; ++i) {
        Complex sum = b[i];
        for (std::size_t k = 0; k < i; ++k) sum -= l(i, k) * y[k];
        y[i] = sum / l(i, i).real();
    }
    for (std::size_t i = n; i-- > 0;) {
        Complex sum = y[i];
        for (std::size_t k = i + 1; k < n; ++k) sum -= std::conj(l(k, i)) * x[k];
        x[i] = sum / l(i, i).real();
    }
    return x;
}

inline Complex inner(const std::vector<Complex>& a, const std::vector<Complex>& b) {
    Complex sum{};
    for (std::size_t i = 0; i < a.size(); ++i) sum += std::conj(a[i]) * b[i];
    return sum;
}
