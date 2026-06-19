void static_overflow() {
    int arr[5];
    int idx = 10;
    // VULN: Accessing index 10 on a size 5 static array
    arr[idx] = 1;
}

void underflow() {
    int arr[5];
    // VULN: Negative index access
    arr[-1] = 0;
}
