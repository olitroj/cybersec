void loop_widening_vuln() {
    int buffer[50];
    int idx = 0;
    
    // The analyzer unrolls 14 times, then assumes infinity.
    for (int i = 0; i < 100; i++) {
        idx = idx + 1;
    }
    
    // VULN: idx is considered to range up to C_MAX, which is > 50
    buffer[idx] = 99;
}
