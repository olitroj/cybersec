int calculate_index(int input);
int path_insensitive_example(int a);
void process_data(int idx);
int path_insensitive_example(int a) {
    if (a > 5) {
        a = 1;
    }
    return a;
}
int calculate_index(int input) {
    int result = input * 2;
    return result + 1;
}
