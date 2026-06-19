void test_pointer_aliasing() {
    int arr[10];
    int *p = arr;
    int *q = p;
    q[5] = 1;
    q[15] = 99;
}
