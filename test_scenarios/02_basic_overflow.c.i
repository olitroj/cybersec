void static_overflow() {
    int arr[5];
    int idx = 10;
    arr[idx] = 1;
}
void underflow() {
    int arr[5];
    arr[-1] = 0;
}
