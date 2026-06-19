// Extern declaration of the global array from sender
extern int shared_global_array[];

void use_global_array_remotely() {
    // UNSAFE: Out of bounds for the global array size of 20
    shared_global_array[25] = 99;
}