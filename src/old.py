import subprocess
import clang.cindex as c
from clang.cindex import CursorKind, TypeKind

C_MIN = -2147483648
C_MAX = 2147483647

# Preprocess the C file
with open("out.i", "w", encoding="utf-8") as f:
    subprocess.run(
        ["clang", "-E", "-P", "main.c"],
        stdout=f,
        text=True
    )

c.Config.set_library_file(
    r"/Library/Developer/CommandLineTools/usr/lib/libclang.dylib"
)

index = c.Index.create()
tu = index.parse("out.i")

class DataFlowAnalyzer:
    def __init__(self):
        # Track memory sizes of static arrays: {'arr': 10}
        self.arrays = {}
        # Track dynamic ranges of integer variables: {'idx': (5, 11)}
        self.vars = {}
        # Track reported vulnerabilities by line to avoid duplicates during loop unrolling
        self.reported_vulns = set()

    def evaluate(self, node):
        """Recursively evaluate an expression to return a (min, max) range."""
        if node.kind == CursorKind.INTEGER_LITERAL:
            val = int(list(node.get_tokens())[0].spelling)
            return (val, val)
            
        elif node.kind == CursorKind.DECL_REF_EXPR:
            var_name = node.spelling
            return self.vars.get(var_name, (C_MIN, C_MAX))
            
        elif node.kind == CursorKind.BINARY_OPERATOR:
            children = list(node.get_children())
            if len(children) != 2:
                 return (C_MIN, C_MAX)
            lhs_range = self.evaluate(children[0])
            rhs_range = self.evaluate(children[1])
            
            # Extract operator by skipping LHS tokens
            tokens = list(node.get_tokens())
            lhs_tokens = list(children[0].get_tokens())
            if len(lhs_tokens) < len(tokens):
                op = tokens[len(lhs_tokens)].spelling
                
                if op == '+':
                    return (lhs_range[0] + rhs_range[0], lhs_range[1] + rhs_range[1])
                elif op == '-':
                    return (lhs_range[0] - rhs_range[1], lhs_range[1] - rhs_range[0])
                elif op == '*':
                    # simplified handling for multiplication bounding
                    bounds = [
                        lhs_range[0] * rhs_range[0], lhs_range[0] * rhs_range[1],
                        lhs_range[1] * rhs_range[0], lhs_range[1] * rhs_range[1]
                    ]
                    return (min(bounds), max(bounds))

            return (C_MIN, C_MAX)
            
        elif node.kind in (CursorKind.UNEXPOSED_EXPR, CursorKind.PAREN_EXPR):
            children = list(node.get_children())
            if children:
                return self.evaluate(children[0])

        elif node.kind == CursorKind.UNARY_OPERATOR:
            tokens = list(node.get_tokens())
            children = list(node.get_children())
            if tokens and tokens[0].spelling == '-' and children:
                val = self.evaluate(children[0])
                return (-val[1], -val[0])

        return (C_MIN, C_MAX)

    def visit(self, node):
        """Top-down AST traversal."""

        if node.kind == CursorKind.VAR_DECL:
            if node.type.kind == TypeKind.CONSTANTARRAY:
                self.arrays[node.spelling] = node.type.element_count
            elif node.type.kind == TypeKind.INT:
                children = list(node.get_children())
                if children: 
                    self.vars[node.spelling] = self.evaluate(children[0])
                else:
                    self.vars[node.spelling] = (C_MIN, C_MAX)

        elif node.kind == CursorKind.BINARY_OPERATOR:
            children = list(node.get_children())
            if len(children) == 2:
                lhs, rhs = children[0], children[1]
                tokens = list(node.get_tokens())
                lhs_tokens = list(lhs.get_tokens())
                if len(lhs_tokens) < len(tokens):
                    op = tokens[len(lhs_tokens)].spelling
                    
                    if op == '=' and lhs.kind in (CursorKind.DECL_REF_EXPR, CursorKind.UNEXPOSED_EXPR):
                        var_name = list(lhs.get_children())[0].spelling if lhs.kind == CursorKind.UNEXPOSED_EXPR else lhs.spelling
                        if var_name:
                             self.vars[var_name] = self.evaluate(rhs)

        elif node.kind == CursorKind.ARRAY_SUBSCRIPT_EXPR:
            children = list(node.get_children())
            if len(children) == 2:
                array_node, index_node = children[0], children[1]
                
                if array_node.kind == CursorKind.UNEXPOSED_EXPR:
                    array_children = list(array_node.get_children())
                    array_name = array_children[0].spelling if array_children else array_node.spelling
                else:
                    array_name = array_node.spelling

                idx_min, idx_max = self.evaluate(index_node)

                if array_name in self.arrays:
                    size = self.arrays[array_name]
                    if idx_max >= size or idx_min < 0:
                        vuln_key = f"{array_name}:{node.location.line}"
                        if vuln_key not in self.reported_vulns:
                            print(f"[!] Vulnerability: Buffer overflow detected. Array '{array_name}' size {size}, accessed at index [{idx_min}, {idx_max}] (Line {node.location.line})")
                            self.reported_vulns.add(vuln_key)

        elif node.kind in (CursorKind.FOR_STMT, CursorKind.WHILE_STMT):
            children = list(node.get_children())
            if not children:
                return

            # The first pass: visit everything to process initialization
            for child in children:
                self.visit(child)
                
            # For subsequent iterations, skip the initialization part of a FOR loop
            loop_body_children = children
            if node.kind == CursorKind.FOR_STMT and len(children) > 1:
                first_toks = list(children[0].get_tokens())
                is_assignment = children[0].kind == CursorKind.BINARY_OPERATOR and len(first_toks) > 1 and first_toks[1].spelling == '='
                if children[0].kind == CursorKind.DECL_STMT or is_assignment:
                    loop_body_children = children[1:]

            # Bounded loop unrolling
            for _ in range(14):
                prev_iter_state = self.vars.copy()
                
                for child in loop_body_children:
                    self.visit(child)
                    
                # Merge state to continually widen bounds based on execution
                merged_state = {}
                all_vars = set(self.vars.keys()) | set(prev_iter_state.keys())
                for var in all_vars:
                    val_new = self.vars.get(var, (C_MIN, C_MAX))
                    val_prev = prev_iter_state.get(var, (C_MIN, C_MAX))
                    merged_state[var] = (min(val_new[0], val_prev[0]), max(val_new[1], val_prev[1]))
                self.vars = merged_state
                
                if prev_iter_state == self.vars:
                    break # Fixed point reached!
            
            # Widening: if variables are still unbounded after 15 iterations, assume infinity
            widened = False
            for var in self.vars:
                if prev_iter_state.get(var) != self.vars[var]:
                    val = self.vars[var]
                    old = prev_iter_state.get(var, (0, 0))
                    new_min = C_MIN if val[0] < old[0] else val[0]
                    new_max = C_MAX if val[1] > old[1] else val[1]
                    self.vars[var] = (new_min, new_max)
                    widened = True
                    
            # Run one last time with widened bounds to catch overflows!
            if widened:
                for child in loop_body_children:
                    self.visit(child)
            return

        elif node.kind == CursorKind.IF_STMT:
            children = list(node.get_children())
            if len(children) >= 2:
                # children[0] is the condition
                self.visit(children[0])
                
                original_state = self.vars.copy()
                
                # Visit the true branch
                self.vars = original_state.copy()
                self.visit(children[1])
                true_state = self.vars.copy()
                
                # Visit the false branch if it exists
                self.vars = original_state.copy()
                if len(children) >= 3:
                    self.visit(children[2])
                false_state = self.vars.copy()
                
                # Merge the states
                merged_state = {}
                all_vars = set(true_state.keys()) | set(false_state.keys()) | set(original_state.keys())
                for var in all_vars:
                    val_t = true_state.get(var, original_state.get(var, (C_MIN, C_MAX)))
                    val_f = false_state.get(var, original_state.get(var, (C_MIN, C_MAX)))
                    merged_state[var] = (min(val_t[0], val_f[0]), max(val_t[1], val_f[1]))
                
                self.vars = merged_state
                return # We handled the children, stop default recursion for this node

        for child in node.get_children():
            self.visit(child)

analyzer = DataFlowAnalyzer()
analyzer.visit(tu.cursor)

print("Final Variable State:", analyzer.vars)
print("Final Arrays Tracking:", analyzer.arrays)

# def print_ast(cursor: c.Cursor):
#     print(f"Cursor: {cursor.type.kind}")
#     for token in list(cursor.get_tokens()):
#         print(f"{token.kind} {token.spelling} {token.kind}")
#
#     for child in cursor.get_children():
#         print_ast(child)
#
# print_ast(tu.cursor)