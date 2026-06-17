import subprocess
import clang.cindex as c
from clang.cindex import CursorKind, TypeKind
import glob
import os
import sys

C_MIN = -2147483648
C_MAX = 2147483647

c.Config.set_library_file(
    r"/Library/Developer/CommandLineTools/usr/lib/libclang.dylib"
)

index = c.Index.create()

class CallGraphAnalyzer:
    def __init__(self):
        self.function_map = {}
        self.global_vars = {}
        self.tus = []

        self.call_stack = []      # List of dictionaries for local vars
        self.reported_vulns = set()
        self.return_val = (C_MIN, C_MAX)
        
        # Unified allocation tracking (for heap and arrays)
        self.allocations = {} # Maps ID -> size: { 'alloc_1': 20 }
        self.next_alloc_id = 1

    def get_var(self, name):
        if self.call_stack and name in self.call_stack[-1]:
            return self.call_stack[-1][name]
        return self.global_vars.get(name, (C_MIN, C_MAX))

    def set_var(self, name, val):
        if self.call_stack and name in self.call_stack[-1]:
            self.call_stack[-1][name] = val
        elif name in self.global_vars:
            self.global_vars[name] = val
        elif self.call_stack:
            self.call_stack[-1][name] = val # new local var
        else:
            self.global_vars[name] = val

    def build_index(self, cursor):
        if cursor.kind == CursorKind.FUNCTION_DECL:
            if cursor.is_definition():
                self.function_map[cursor.spelling] = cursor
        elif cursor.kind == CursorKind.VAR_DECL:
            if cursor.lexical_parent and cursor.lexical_parent.kind == CursorKind.TRANSLATION_UNIT:
                if cursor.type.kind == TypeKind.CONSTANTARRAY:
                    alloc_id = f"alloc_{self.next_alloc_id}"
                    self.next_alloc_id += 1
                    self.allocations[alloc_id] = cursor.type.element_count
                    self.global_vars[cursor.spelling] = alloc_id
                elif cursor.type.kind == TypeKind.INT:
                    children = list(cursor.get_children())
                    if children:
                        self.global_vars[cursor.spelling] = self.evaluate_no_call(children[0])
                    else:
                        self.global_vars[cursor.spelling] = (C_MIN, C_MAX)
        for child in cursor.get_children():
            self.build_index(child)

    def evaluate_no_call(self, node):
        if node.kind == CursorKind.INTEGER_LITERAL:
            val = int(list(node.get_tokens())[0].spelling)
            return (val, val)
        return (C_MIN, C_MAX)

    def evaluate(self, node):
        if node.kind == CursorKind.INTEGER_LITERAL:
            val = int(list(node.get_tokens())[0].spelling)
            return (val, val)
        elif node.kind == CursorKind.DECL_REF_EXPR:
            return self.get_var(node.spelling)
        elif node.kind == CursorKind.CALL_EXPR:
            return self.handle_call(node)
        elif node.kind == CursorKind.BINARY_OPERATOR:
            children = list(node.get_children())
            if len(children) != 2: return (C_MIN, C_MAX)
            lhs_range = self.evaluate(children[0])
            rhs_range = self.evaluate(children[1])
            
            # Prevent crashing if we try to do math on a pointer ID
            if isinstance(lhs_range, str) or isinstance(rhs_range, str):
                return (C_MIN, C_MAX)

            tokens = list(node.get_tokens())
            lhs_tokens = list(children[0].get_tokens())
            if len(lhs_tokens) < len(tokens):
                op = tokens[len(lhs_tokens)].spelling
                if op == '+': return (lhs_range[0] + rhs_range[0], lhs_range[1] + rhs_range[1])
                elif op == '-': return (lhs_range[0] - rhs_range[1], lhs_range[1] - rhs_range[0])
                elif op == '*':
                    bounds = [
                        lhs_range[0] * rhs_range[0], lhs_range[0] * rhs_range[1],
                        lhs_range[1] * rhs_range[0], lhs_range[1] * rhs_range[1]
                    ]
                    return (min(bounds), max(bounds))
            return (C_MIN, C_MAX)
        elif node.kind in (CursorKind.UNEXPOSED_EXPR, CursorKind.PAREN_EXPR):
            children = list(node.get_children())
            if children:
                # If the unexposed expr wraps a function call or ref, evaluate it
                return self.evaluate(children[0])
        elif node.kind == CursorKind.UNARY_OPERATOR:
            tokens = list(node.get_tokens())
            children = list(node.get_children())
            if tokens and tokens[0].spelling == '-' and children:
                val = self.evaluate(children[0])
                return (-val[1], -val[0])
        return (C_MIN, C_MAX)

    def handle_call(self, node):
        func_name = None
        children = list(node.get_children())
        if not children:
            return (C_MIN, C_MAX)
            
        if children[0].kind in (CursorKind.DECL_REF_EXPR, CursorKind.UNEXPOSED_EXPR):
            func_name = children[0].spelling
            args_nodes = children[1:]
        else:
            func_name = node.spelling
            args_nodes = children
            
        if not func_name and node.spelling:
            func_name = node.spelling

        if func_name == "malloc":
            if args_nodes:
                size_range = self.evaluate(args_nodes[0])
                if not isinstance(size_range, str): # Safety check
                    alloc_id = f"alloc_{self.next_alloc_id}"
                    self.next_alloc_id += 1
                    # In a real system, we'd divide by sizeof(type). We'll store raw bytes/elements
                    self.allocations[alloc_id] = size_range[1]
                    return alloc_id
            return (C_MIN, C_MAX)

        if func_name in self.function_map:
            func_cursor = self.function_map[func_name]
            params = [c for c in func_cursor.get_children() if c.kind == CursorKind.PARM_DECL]
            
            arg_ranges = [self.evaluate(arg) for arg in args_nodes]
            
            new_frame = {}
            for i, param in enumerate(params):
                if i < len(arg_ranges):
                    new_frame[param.spelling] = arg_ranges[i]
                else:
                    new_frame[param.spelling] = (C_MIN, C_MAX)
            
            self.call_stack.append(new_frame)
            
            old_return = self.return_val
            self.return_val = (C_MIN, C_MAX)
            
            for c in func_cursor.get_children():
                if c.kind == CursorKind.COMPOUND_STMT:
                    self.visit(c)
                    
            ret_val = self.return_val
            
            self.call_stack.pop()
            self.return_val = old_return
            
            return ret_val

        return (C_MIN, C_MAX)

    def visit(self, node):
        if node.kind == CursorKind.VAR_DECL:
            if node.type.kind == TypeKind.CONSTANTARRAY:
                alloc_id = f"alloc_{self.next_alloc_id}"
                self.next_alloc_id += 1
                self.allocations[alloc_id] = node.type.element_count
                self.set_var(node.spelling, alloc_id)
            elif node.type.kind in (TypeKind.INT, TypeKind.POINTER):
                children = list(node.get_children())
                if children: 
                    self.set_var(node.spelling, self.evaluate(children[0]))
                else:
                    self.set_var(node.spelling, (C_MIN, C_MAX))

        elif node.kind == CursorKind.RETURN_STMT:
            children = list(node.get_children())
            if children:
                self.return_val = self.evaluate(children[0])

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
                             self.set_var(var_name, self.evaluate(rhs))

        elif node.kind == CursorKind.CALL_EXPR:
            self.handle_call(node)

        elif node.kind == CursorKind.ARRAY_SUBSCRIPT_EXPR:
            children = list(node.get_children())
            if len(children) == 2:
                array_node, index_node = children[0], children[1]
                
                if array_node.kind == CursorKind.UNEXPOSED_EXPR:
                    array_children = list(array_node.get_children())
                    array_name = array_children[0].spelling if array_children else array_node.spelling
                else:
                    array_name = array_node.spelling

                pointer_val = self.evaluate(array_node)
                idx_range = self.evaluate(index_node)
                
                if isinstance(idx_range, tuple):
                    idx_min, idx_max = idx_range
                    
                    if isinstance(pointer_val, str) and pointer_val.startswith("alloc_"):
                        size = self.allocations.get(pointer_val)
                        if size is not None:
                            if idx_max >= size or idx_min < 0:
                                file_name = node.location.file.name if node.location.file else "unknown"
                                file_base = os.path.basename(file_name)
                                vuln_key = f"{file_base}:{array_name}:{node.location.line}"
                                if vuln_key not in self.reported_vulns:
                                    print(f"[!] Vulnerability: Buffer overflow detected in {file_base}. Array '{array_name}' size {size}, accessed at index [{idx_min}, {idx_max}] (Line {node.location.line})")
                                    self.reported_vulns.add(vuln_key)

        elif node.kind in (CursorKind.FOR_STMT, CursorKind.WHILE_STMT):
            children = list(node.get_children())
            if not children: return

            for child in children:
                self.visit(child)
                
            loop_body_children = children
            if node.kind == CursorKind.FOR_STMT and len(children) > 1:
                first_toks = list(children[0].get_tokens())
                is_assignment = children[0].kind == CursorKind.BINARY_OPERATOR and len(first_toks) > 1 and first_toks[1].spelling == '='
                if children[0].kind == CursorKind.DECL_STMT or is_assignment:
                    loop_body_children = children[1:]

            for _ in range(14):
                if not self.call_stack: break
                prev_iter_state = self.call_stack[-1].copy()
                
                for child in loop_body_children:
                    self.visit(child)
                    
                merged_state = {}
                all_vars = set(self.call_stack[-1].keys()) | set(prev_iter_state.keys())
                for var in all_vars:
                    val_new = self.call_stack[-1].get(var, (C_MIN, C_MAX))
                    val_prev = prev_iter_state.get(var, (C_MIN, C_MAX))
                    if isinstance(val_new, tuple) and isinstance(val_prev, tuple):
                        merged_state[var] = (min(val_new[0], val_prev[0]), max(val_new[1], val_prev[1]))
                    else:
                         merged_state[var] = val_new if val_new == val_prev else (C_MIN, C_MAX)
                self.call_stack[-1] = merged_state
                
                if prev_iter_state == self.call_stack[-1]:
                    break
            
            if self.call_stack:
                widened = False
                for var in list(self.call_stack[-1].keys()):
                    if prev_iter_state.get(var) != self.call_stack[-1][var]:
                        val = self.call_stack[-1][var]
                        old = prev_iter_state.get(var, (0, 0))
                        if isinstance(val, tuple) and isinstance(old, tuple):
                            new_min = C_MIN if val[0] < old[0] else val[0]
                            new_max = C_MAX if val[1] > old[1] else val[1]
                            self.call_stack[-1][var] = (new_min, new_max)
                            widened = True
                if widened:
                    for child in loop_body_children:
                        self.visit(child)
            return

        elif node.kind == CursorKind.IF_STMT:
            children = list(node.get_children())
            if len(children) >= 2:
                self.visit(children[0])
                if not self.call_stack:
                    for c in children[1:]: self.visit(c)
                    return
                
                original_state = self.call_stack[-1].copy()
                
                self.call_stack[-1] = original_state.copy()
                self.visit(children[1])
                true_state = self.call_stack[-1].copy()
                
                self.call_stack[-1] = original_state.copy()
                if len(children) >= 3:
                    self.visit(children[2])
                false_state = self.call_stack[-1].copy()
                
                merged_state = {}
                all_vars = set(true_state.keys()) | set(false_state.keys()) | set(original_state.keys())
                for var in all_vars:
                    val_t = true_state.get(var, original_state.get(var, (C_MIN, C_MAX)))
                    val_f = false_state.get(var, original_state.get(var, (C_MIN, C_MAX)))
                    
                    if isinstance(val_t, tuple) and isinstance(val_f, tuple):
                        merged_state[var] = (min(val_t[0], val_f[0]), max(val_t[1], val_f[1]))
                    elif val_t == val_f:
                        merged_state[var] = val_t # Preserve pointer ID if unchanged
                    else:
                        merged_state[var] = (C_MIN, C_MAX) # Lost track
                
                self.call_stack[-1] = merged_state
                return

        for child in node.get_children():
            self.visit(child)

    def analyze_project(self, target_dir):
        # Allow running on a specified directory recursively
        c_files = glob.glob(os.path.join(target_dir, "**/*.c"), recursive=True)
        if not c_files:
            c_files = glob.glob(os.path.join(target_dir, "*.c"))
            if not c_files:
                print(f"No .c files found in {target_dir}")
                return

        print(f"[*] Phase 1: Indexing {len(c_files)} files...")
        
        for c_file in c_files:
            out_i = f"{c_file}.i"
            with open(out_i, "w", encoding="utf-8") as f:
                subprocess.run(["clang", "-E", "-P", c_file], stdout=f, text=True)
            tu = index.parse(out_i)
            self.tus.append(tu) # Keep alive
            self.build_index(tu.cursor)
            
        print(f"[*] Found {len(self.function_map)} functions.")
        
        print("[*] Phase 2: Inter-procedural Analysis (Starting from 'main')")
        if "main" not in self.function_map:
             print("[!] Error: No 'main' function found. Cannot perform call-graph analysis.")
             return
             
        self.call_stack.append({})
        
        main_cursor = self.function_map["main"]
        for c in main_cursor.get_children():
             if c.kind == CursorKind.COMPOUND_STMT:
                 self.visit(c)

        print("[*] Analysis complete.")

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    
    analyzer = CallGraphAnalyzer()
    analyzer.analyze_project(target_dir)

if __name__ == "__main__":
    main()
