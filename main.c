#include "main.h"

int main() {
    int local_buffer[5];
    
    // --- SCENARIO 1: Safe inter-procedural call ---
    // calculate_index(1) returns 3. 
    // local_buffer[3] is SAFE. (No warning expected)
    int safe_idx = calculate_index(1); 
    local_buffer[safe_idx] = 100; 
    
    // --- SCENARIO 2: Path Insensitivity (False Positive) ---
    // Returns 1 in reality, but analyzer thinks it returns (1, 6).
    // local_buffer size is 5. Since max is 6, it FLAGS VULNERABILITY!
    int risky_idx = path_insensitive_example(6); 
    local_buffer[risky_idx] = 200; 

    // --- SCENARIO 3: True Buffer Overflow across files ---
    // calculate_index(5) returns 11.
    // Passes 11 to process_data, which writes to global_arr[11].
    // global_arr is size 10. FLAGS VULNERABILITY!
    int bad_idx = calculate_index(5); 
    process_data(bad_idx); 

    // --- SCENARIO 4: Loop Widening ---
    // Loop unrolls 14 times, then the analyzer assumes `loop_idx` goes to infinity.
    // FLAGS VULNERABILITY!
    int loop_idx = 0;
    for (int i = 0; i < 20; i++) {
        loop_idx = i;
    }
    local_buffer[loop_idx] = 300; 

    return 0;
}
