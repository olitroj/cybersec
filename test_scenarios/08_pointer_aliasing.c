void test_pointer_aliasing() {
    int arr[10];
    int *p = arr;
    int *q = p;
    
    // SAFE
    q[5] = 1;
    
    // UNSAFE: Should trigger vulnerability on 'q' or 'arr'
    q[15] = 99;
}