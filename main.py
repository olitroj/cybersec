import clang.cindex as clang
import os
clang.Config.set_library_path(os.environ.get("LIBCLANG_PATH"))

index = clang.Index.create()

import src.tu as tu
buffers, ints = tu.scan_tu(index, "test/ctest/function_test.c", {}, {})

print(f"Buffers: {buffers}")
print(f"Ints: {ints}")