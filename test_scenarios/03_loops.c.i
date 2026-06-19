void loop_widening_vuln() {
    int buffer[50];
    int idx = 0;
    for (int i = 0; i < 100; i++) {
        idx = idx + 1;
    }
    buffer[idx] = 99;
}
