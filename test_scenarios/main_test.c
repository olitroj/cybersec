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
    
    void test_pointer_aliasing();
    test_pointer_aliasing();
    
    void use_global_array_remotely();
    use_global_array_remotely();
    
    // Passing 10 triggers the path insensitivity false positive
    path_insensitivity_false_positive(10);
    
    return 0;
}