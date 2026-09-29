CXX ?= g++
FLAGS = -std=c++17 -Wall -Wextra -Wpedantic
HEADERS = beamformer.hpp delay_filter.hpp fft.hpp fixed.hpp geometry.hpp linalg.hpp mpdr.hpp

design_weights: design_weights.cpp $(HEADERS)
	$(CXX) $(FLAGS) -O2 -o $@ design_weights.cpp

design_weights_check: design_weights.cpp $(HEADERS)
	$(CXX) $(FLAGS) -O1 -g -fsanitize=address,undefined -o $@ design_weights.cpp

clean:
	rm -f design_weights design_weights_check

.PHONY: clean
