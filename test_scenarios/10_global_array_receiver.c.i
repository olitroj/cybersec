
extern int shared_global_array[];
void use_global_array_remotely() {
    shared_global_array[25] = 99;
}
