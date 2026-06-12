import clang.cindex as c
c.Config.set_library_file(r"/Library/Developer/CommandLineTools/usr/lib/libclang.dylib")
index = c.Index.create()
tu = index.parse("tmp.c", unsaved_files=[("tmp.c", "void *malloc(unsigned long size); void test() { int *p = malloc(5); }")])

def print_ast(cursor, depth=0):
    print("  " * depth + f"{cursor.kind} {cursor.spelling}")
    for child in cursor.get_children():
        print_ast(child, depth + 1)

for child in tu.cursor.get_children():
    if child.spelling == "test":
        print_ast(child)
