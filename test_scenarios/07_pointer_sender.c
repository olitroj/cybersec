#include <stdlib.h>

// Forward declaration for the function in the other file
void manipulate_array(int *arr, int index);

void test_cross_file_pointers() {
    // 1. Allocate size 10 on the heap ("heap_X")
    int *dynamic_arr = malloc(10);
    
    // 2. Safe access locally
    dynamic_arr[5] = 1;
    
    // 3. Pass the pointer to another file with a SAFE index
    manipulate_array(dynamic_arr, 8);
    
    // 4. Pass the pointer to another file with an UNSAFE index
    // The analyzer should flag this access occurring inside manipulate_array
    manipulate_array(dynamic_arr, 15);
}
