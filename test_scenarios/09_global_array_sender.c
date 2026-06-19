// Global array defined in one file
int shared_global_array[20];

void use_global_array_locally() {
    // SAFE
    shared_global_array[10] = 1;
}