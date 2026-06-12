import clang.cindex as c
from main import CallGraphAnalyzer, index

tu = index.parse("tmp.c", unsaved_files=[("tmp.c", "void *malloc(unsigned long size); void test() { int *p = malloc(5); p[10] = 42; }")])
analyzer = CallGraphAnalyzer()
analyzer.call_stack.append({})
analyzer.array_stack.append({})
for child in tu.cursor.get_children():
    if child.spelling == "test":
        for ch in child.get_children():
            if ch.kind == c.CursorKind.COMPOUND_STMT:
                analyzer.visit(ch)
print("VULNS:", analyzer.reported_vulns)
print("VARS:", analyzer.call_stack[-1])
print("HEAP:", analyzer.heap_allocations)
