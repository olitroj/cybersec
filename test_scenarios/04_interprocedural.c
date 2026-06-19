int get_bad_index() {
    return 10;
}

void cross_file_vuln() {
    int arr[5];
    // VULN: Resolves to 10 across a function call
    arr[get_bad_index()] = 42;
}
