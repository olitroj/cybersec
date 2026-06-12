int get_bad_index() {
    return 10;
}
void cross_file_vuln() {
    int arr[5];
    arr[get_bad_index()] = 42;
}
