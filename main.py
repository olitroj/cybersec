import subprocess
with open("out.i", "w", encoding="utf-8") as f:
    subprocess.run(
        ["clang", "-E", "-P", "main.c"],
        stdout=f,
        text=True
    )

import clang.cindex as c
c.Config.set_library_file(
    r"C:\Program Files\LLVM\bin\libclang.dll"
)

index = c.Index.create()
tu = index.parse("out.i")

def traverse(node: c.Cursor, indent=0):
    print(
        "  " * indent +
        f"{node.kind} : {[t.spelling for t in node.get_tokens()]}"
    )

    for child in node.get_children():
        traverse(child, indent + 1)

traverse(tu.cursor)