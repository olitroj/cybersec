void path_insensitivity_false_positive(int input) {
    int arr[5];
    int a = input;
    if (a > 3) {
        a = 2;
    }
    arr[a] = 1;
}
