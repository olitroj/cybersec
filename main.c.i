int calculate_index(int input);
int path_insensitive_example(int a);
void process_data(int idx);

int main() {
    int local_buffer[5];
    int safe_idx = calculate_index(1);
    local_buffer[safe_idx] = 100;
    int risky_idx = path_insensitive_example(6);
    local_buffer[risky_idx] = 200;
    int bad_idx = calculate_index(5);
    process_data(bad_idx);
    int loop_idx = 0;
    for (int i = 0; i < 20; i++) {
        loop_idx = i;
    }
    local_buffer[loop_idx] = 300;
    return 0;
}
