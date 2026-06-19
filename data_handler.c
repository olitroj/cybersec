#include "main.h"

// A global array sized via a macro
int global_arr[MAX_SIZE];

void process_data(int idx) {
    // If idx is out of bounds (e.g., < 0 or >= 10), it should flag.
    global_arr[idx] = 42; 
}
