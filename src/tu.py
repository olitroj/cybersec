from clang.cindex import *

C_MIN = -2147483648
C_MAX = 2147483647

def scan_tu(index: Index, filepath: str, extern_buffers: dict, extern_ints: dict):
    tu = index.parse(filepath)
    buffers = {}
    ints = {}
    _traverse(tu.cursor, buffers, ints, extern_buffers, extern_ints)
    return (buffers, ints)

'''
    Recursevly traverses the AST of a single TU. Performs operations based on the current node. 
'''
def _traverse(cursor: Cursor, buffers: dict, ints: dict, extern_buffers: dict, extern_ints: dict, indent = 0):
    print(
        "  " * indent +
        f"{cursor.kind} {cursor.spelling} {cursor.type.kind} {cursor.type.spelling} {cursor.type.get_array_size()} : {[t.spelling for t in cursor.get_tokens()]}"
    )

    if cursor.kind == CursorKind.VAR_DECL and cursor.type.kind == TypeKind.CONSTANTARRAY:
        _constant_array_decl(cursor, buffers)
    elif cursor.kind == CursorKind.VAR_DECL and cursor.type.kind == TypeKind.INT:
        _integer_decl(cursor, ints)
    elif cursor.kind == CursorKind.FUNCTION_DECL:
        _function_decl(cursor, ints)

    for child in cursor.get_children():
        _traverse(child, buffers, ints, extern_buffers, extern_ints, indent+1)


def _constant_array_decl(cursor: Cursor, buffers: dict):
    # TODO : VLAs
    buffers[cursor.spelling] = cursor.type.get_array_size()

def _integer_decl(cursor: Cursor, ints: dict):
    # TODO : Add external int linkage
    children = list(cursor.get_children())
    if not children:
        ints[cursor.spelling] = (C_MIN, C_MAX)
    else:
        ints[cursor.spelling] = _evaluate_expr(children[0], ints)

def _function_decl(cursor: Cursor, ints: dict):
    # TODO : Finish this
    children = list(cursor.get_children())
    


'''
    Evaluates an expressions pointed at by the cursor.
'''
def _evaluate_expr(cursor: Cursor, ints: dict) -> tuple:
    if cursor.kind == CursorKind.INTEGER_LITERAL:
        # TODO : Add float and other integer type casting
        val = int(list(cursor.get_tokens())[0].spelling)
        return (val, val)
    elif cursor.kind == CursorKind.BINARY_OPERATOR:
        val1 = _evaluate_expr(list(cursor.get_children())[0], ints)
        val2 = _evaluate_expr(list(cursor.get_children())[1], ints)
        op = cursor.spelling
        # TODO : Add more operators
        if op == '+':
            return (val1[0] + val2[0], val1[1] + val2[1])
        elif op == '-':
            return (val1[0] - val2[0], val1[1] - val2[1])
        elif op == '*':
            return (val1[0] * val2[0], val1[1] * val2[1])
        elif op == '/':
            return (val1[0] // val2[0], val1[1] // val2[1])
    elif cursor.kind == CursorKind.DECL_REF_EXPR and (cursor.type.kind == TypeKind.INT or cursor.type.kind == TypeKind.FUNCTIONNOPROTO):
        if cursor.spelling in ints:
            return ints[cursor.spelling]
    
    for child in cursor.get_children():
        return _evaluate_expr(child, ints)