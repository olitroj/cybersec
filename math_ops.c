#include "main.h"

// Demonstrates the exact path insensitivity limitation you asked about
int path_insensitive_example(int a) {
    if (a > 5) {
        a = 1;
    }
    // If input is 6, analyzer merges true (1) and false (6) -> returns (1, 6)
    return a; 
}

// Standard inter-procedural math calculation
int calculate_index(int input) {
    int result = input * 2;
    return result + 1; 
}
