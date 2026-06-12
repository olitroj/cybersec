#include <stdlib.h>

void heap_overflow() {
    int *p = malloc(10);
    // VULN: Accessing index 15 on a size 10 heap allocation
    p[15] = 42;
}

void safe_heap() {
    int *q = malloc(20);
    q[19] = 100; // SAFE
}
