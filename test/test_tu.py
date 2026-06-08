import clang.cindex as clang
import os
clang.Config.set_library_path(os.environ.get("LIBCLANG_PATH"))

index = clang.Index.create()

from src.tu import scan_tu

def test_scan_arrays():
    buffers, _ = scan_tu(index, "test/ctest/array_test.c", {}, {})
    assert(buffers == {
        'a': 5,
        'b': 6,
        'c': 3
    })

def test_scan_integers():
    _, ints = scan_tu(index, "test/ctest/integer_test.c", {}, {})
    assert(ints == {
        'a': (-2147483648, 2147483647),
        'b': (5, 5),
        'c': (11, 11),
        'd': (47, 47)
    })