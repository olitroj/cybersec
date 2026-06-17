void manipulate_array(int *arr, int index) {
    // VULN: If the passed array is smaller than the index, this will overflow.
    arr[index] = 99;
}
