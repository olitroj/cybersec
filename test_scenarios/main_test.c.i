int main() {
    heap_overflow();
    safe_heap();
    static_overflow();
    underflow();
    loop_widening_vuln();
    cross_file_vuln();
    void test_cross_file_pointers();
    test_cross_file_pointers();
    path_insensitivity_false_positive(10);
    return 0;
}
