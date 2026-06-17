int main() {
    // We must call the functions so the interprocedural analyzer visits them
    heap_overflow();
    safe_heap();
    static_overflow();
    underflow();
    loop_widening_vuln();
    cross_file_vuln();
    
    // Test passing dynamic arrays across files
    void test_cross_file_pointers(); // Forward decl
    test_cross_file_pointers();
    
    // Passing 10 triggers the path insensitivity false positive
    path_insensitivity_false_positive(10);
    
    return 0;
}