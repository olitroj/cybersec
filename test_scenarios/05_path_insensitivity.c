void path_insensitivity_false_positive(int input) {
    int arr[5];
    int a = input;
    
    if (a > 3) {
        a = 2;
    }
    
    // If input is 4, the analyzer merges the true branch (2) 
    // and false branch (4). It assumes a is (2, 4).
    // Array is size 5, so [2, 4] is SAFE. 
    // BUT if input is 10, it merges true (2) and false (10).
    // Range becomes (2, 10). 10 is > 5. 
    // VULN (False Positive if input is 10): 
    arr[a] = 1;
}
