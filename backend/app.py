#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import tempfile
import os
import json
import sys
import traceback

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({"status": "API is running"})

@app.route('/analyze', methods=['POST'])
def analyze_code():
    data = request.json
    code = data.get('code', '')
    language = data.get('language', 'python')
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        if language.lower() == 'python':
            result = analyze_python_code(code)
        elif language.lower() == 'c':
            result = analyze_c_code(code)
        else:
            return jsonify({"error": "Unsupported language"}), 400
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500

def analyze_python_code(code):
    # 创建临时文件来存储代码和分析结果
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name
    
    # 创建一个修改版本的代码，添加跟踪语句
    instrumented_code = instrument_python_code(code)
    with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as instrumented_file:
        instrumented_file.write(instrumented_code.encode('utf-8'))
        instrumented_file_path = instrumented_file.name
    
    try:
        # 运行修改后的代码来收集执行信息
        result = subprocess.run(
            [sys.executable, instrumented_file_path],
            capture_output=True,
            text=True,
            timeout=5  # 设置超时，防止无限循环
        )
        
        # 解析输出以获取执行跟踪
        execution_trace = parse_python_execution_trace(result.stdout)
        
        # 进行静态分析以获取代码结构
        code_structure = analyze_python_structure(code)
        
        return {
            "status": "success",
            "execution_trace": execution_trace,
            "code_structure": code_structure,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Code execution timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file_path)
            os.unlink(instrumented_file_path)
        except:
            pass

def instrument_python_code(code):
    """向Python代码添加跟踪语句，以便跟踪变量和执行流程"""
    import ast
    import astor
    
    # 尝试使用AST进行代码插桩
    try:
        # 解析代码为AST
        tree = ast.parse(code)
        
        # 定义跟踪函数和初始化代码
        trace_setup = """
import sys
import json
import traceback

_trace_data = []
_call_stack = []

def _trace_line(line_no, locals_dict, call_depth=0):
    # 过滤掉内部变量
    filtered_locals = {}
    for k, v in locals_dict.items():
        if k.startswith('_') and k != '_call_stack':
            continue
        if k == 'locals_dict':
            continue
            
        # 处理不同类型的变量
        try:
            if isinstance(v, (int, float, bool, str, type(None))):
                filtered_locals[k] = repr(v)
            elif isinstance(v, (list, tuple)):
                if len(v) > 5:
                    filtered_locals[k] = f"{type(v).__name__}([{', '.join(repr(x) for x in v[:5])}...], len={len(v)})"
                else:
                    filtered_locals[k] = f"{type(v).__name__}({repr(v)})"
            elif isinstance(v, dict):
                if len(v) > 3:
                    items = list(v.items())[:3]
                    filtered_locals[k] = f"dict({{{', '.join(f'{repr(k)}: {repr(v)}' for k, v in items)}...}}, len={len(v)})"
                else:
                    filtered_locals[k] = f"dict({repr(v)})"
            else:
                filtered_locals[k] = f"{type(v).__name__}({repr(v)})"
        except:
            filtered_locals[k] = f"{type(v).__name__}(...)"
    
    # 创建跟踪数据
    trace_entry = {
        'line': line_no,
        'variables': filtered_locals,
        'call_stack': list(_call_stack)
    }
    _trace_data.append(trace_entry)
    
    # 输出跟踪数据
    print(f'TRACE:{json.dumps(trace_entry)}')

def _trace_call(func_name, line_no):
    _call_stack.append({'name': func_name, 'line': line_no})
    
def _trace_return(func_name):
    if _call_stack and _call_stack[-1]['name'] == func_name:
        _call_stack.pop()
"""
        
        # 创建包含跟踪设置的模块
        setup_ast = ast.parse(trace_setup)
        
        # 定义AST转换器来添加跟踪调用
        class TraceTransformer(ast.NodeTransformer):
            def __init__(self):
                self.function_stack = []
            
            def visit_Module(self, node):
                # 添加跟踪设置到模块开头
                node.body = setup_ast.body + node.body
                return self.generic_visit(node)
            
            def visit_FunctionDef(self, node):
                # 记录当前函数
                self.function_stack.append(node.name)
                
                # 添加函数调用跟踪
                trace_call = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id='_trace_call', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=node.name),
                            ast.Constant(value=node.lineno)
                        ],
                        keywords=[]
                    )
                )
                
                # 添加函数返回跟踪到每个return语句
                new_body = []
                for item in node.body:
                    if isinstance(item, ast.Return):
                        trace_return = ast.Expr(
                            value=ast.Call(
                                func=ast.Name(id='_trace_return', ctx=ast.Load()),
                                args=[ast.Constant(value=node.name)],
                                keywords=[]
                            )
                        )
                        new_body.append(trace_return)
                    new_body.append(item)
                
                # 更新函数体
                node.body = [trace_call] + new_body
                
                # 继续处理函数体
                self.generic_visit(node)
                
                # 离开函数
                self.function_stack.pop()
                return node
            
            def visit_Assign(self, node):
                # 在赋值后添加跟踪
                self.generic_visit(node)
                trace_expr = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id='_trace_line', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=node.lineno),
                            ast.Call(
                                func=ast.Name(id='locals', ctx=ast.Load()),
                                args=[],
                                keywords=[]
                            ),
                            ast.Constant(value=len(self.function_stack))
                        ],
                        keywords=[]
                    )
                )
                return [node, trace_expr]
            
            def visit_If(self, node):
                # 在if语句后添加跟踪
                self.generic_visit(node)
                trace_expr = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id='_trace_line', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=node.lineno),
                            ast.Call(
                                func=ast.Name(id='locals', ctx=ast.Load()),
                                args=[],
                                keywords=[]
                            ),
                            ast.Constant(value=len(self.function_stack))
                        ],
                        keywords=[]
                    )
                )
                return [node, trace_expr]
            
            def visit_For(self, node):
                # 在for循环后添加跟踪
                self.generic_visit(node)
                trace_expr = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id='_trace_line', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=node.lineno),
                            ast.Call(
                                func=ast.Name(id='locals', ctx=ast.Load()),
                                args=[],
                                keywords=[]
                            ),
                            ast.Constant(value=len(self.function_stack))
                        ],
                        keywords=[]
                    )
                )
                return [node, trace_expr]
            
            def visit_While(self, node):
                # 在while循环后添加跟踪
                self.generic_visit(node)
                trace_expr = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id='_trace_line', ctx=ast.Load()),
                        args=[
                            ast.Constant(value=node.lineno),
                            ast.Call(
                                func=ast.Name(id='locals', ctx=ast.Load()),
                                args=[],
                                keywords=[]
                            ),
                            ast.Constant(value=len(self.function_stack))
                        ],
                        keywords=[]
                    )
                )
                return [node, trace_expr]
        
        # 应用转换器
        transformer = TraceTransformer()
        transformed_tree = transformer.visit(tree)
        
        # 添加最终跟踪数据输出
        final_print = ast.Expr(
            value=ast.Call(
                func=ast.Name(id='print', ctx=ast.Load()),
                args=[ast.Constant(value='TRACE_END')],
                keywords=[]
            )
        )
        transformed_tree.body.append(final_print)
        
        # 将AST转换回代码
        try:
            # 尝试使用astor库（如果可用）
            instrumented_code = astor.to_source(transformed_tree)
        except (ImportError, NameError):
            # 如果astor不可用，尝试使用ast.unparse（Python 3.9+）
            if hasattr(ast, 'unparse'):
                instrumented_code = ast.unparse(transformed_tree)
            else:
                # 如果都不可用，回退到简单的行插桩
                raise ImportError("需要astor库或Python 3.9+")
        
        return instrumented_code
        
    except (SyntaxError, ImportError) as e:
        # 如果AST处理失败，回退到简单的行插桩
        print(f"AST插桩失败，回退到简单插桩: {str(e)}")
        lines = code.split('\n')
        instrumented_lines = []
        
        # 添加跟踪模块
        instrumented_lines.append("import sys")
        instrumented_lines.append("import json")
        instrumented_lines.append("_trace_data = []")
        instrumented_lines.append("_call_stack = []")
        
        # 添加跟踪函数
        instrumented_lines.append("def _trace_line(line_no, locals_dict):")  
        instrumented_lines.append("    filtered_locals = {k: repr(v) for k, v in locals_dict.items() if not k.startswith('_') and k != 'locals_dict'}")
        instrumented_lines.append("    trace_entry = {'line': line_no, 'variables': filtered_locals, 'call_stack': list(_call_stack)}")
        instrumented_lines.append("    _trace_data.append(trace_entry)")
        instrumented_lines.append("    print(f'TRACE:{json.dumps(trace_entry)}')")
        
        # 添加函数跟踪函数
        instrumented_lines.append("def _trace_call(func_name, line_no):")
        instrumented_lines.append("    _call_stack.append({'name': func_name, 'line': line_no})")
        
        instrumented_lines.append("def _trace_return(func_name):")
        instrumented_lines.append("    if _call_stack and _call_stack[-1]['name'] == func_name:")
        instrumented_lines.append("        _call_stack.pop()")
        
        # 在每行代码后添加跟踪调用
        for i, line in enumerate(lines):
            instrumented_lines.append(line)
            # 跳过空行和注释行
            if line.strip() and not line.strip().startswith('#'):
                # 检测函数定义
                if line.strip().startswith('def ') and '(' in line and ')' in line:
                    func_name = line.strip()[4:].split('(')[0]
                    indent = len(line) - len(line.lstrip())
                    trace_call = ' ' * indent + f"_trace_call('{func_name}', {i+1})"
                    instrumented_lines.append(trace_call)
                # 检测返回语句
                elif line.strip().startswith('return '):
                    indent = len(line) - len(line.lstrip())
                    # 尝试找出当前函数名（简化版）
                    func_name = "unknown"
                    for j in range(i, -1, -1):
                        if lines[j].strip().startswith('def '):
                            func_name = lines[j].strip()[4:].split('(')[0]
                            break
                    trace_return = ' ' * indent + f"_trace_return('{func_name}')"
                    instrumented_lines.append(trace_return)
                
                # 缩进级别与原始代码行相同
                indent = len(line) - len(line.lstrip())
                trace_call = ' ' * indent + f"_trace_line({i+1}, locals())"
                instrumented_lines.append(trace_call)
        
        # 添加最终跟踪数据输出
        instrumented_lines.append("print('TRACE_END')")
        
        return '\n'.join(instrumented_lines)

def parse_python_execution_trace(output):
    """解析Python执行跟踪输出"""
    trace_lines = [line for line in output.split('\n') if line.startswith('TRACE:')]
    execution_trace = []
    
    for line in trace_lines:
        try:
            # 提取JSON部分
            json_str = line[len('TRACE:'):]
            trace_data = json.loads(json_str)
            
            # 增强跟踪数据
            if 'line' in trace_data:
                # 确保变量字段存在
                if 'variables' not in trace_data:
                    trace_data['variables'] = {}
                
                # 确保调用栈字段存在
                if 'call_stack' not in trace_data:
                    trace_data['call_stack'] = []
                
                # 添加内存信息
                trace_data['memory'] = {
                    'stack': [],
                    'heap': []
                }
                
                # 处理变量，区分栈和堆
                for var_name, var_value in trace_data['variables'].items():
                    # 简单判断是否为基本类型
                    is_primitive = True
                    if var_value.startswith('list(') or var_value.startswith('dict(') or \
                       var_value.startswith('tuple(') or var_value.startswith('set(') or \
                       'object' in var_value.lower() or 'instance' in var_value.lower():
                        is_primitive = False
                    
                    if is_primitive:
                        trace_data['memory']['stack'].append({
                            'name': var_name,
                            'value': var_value,
                            'type': 'primitive'
                        })
                    else:
                        # 为引用类型创建一个唯一ID
                        heap_id = f"id_{len(trace_data['memory']['heap'])}"
                        
                        # 在栈中添加引用
                        trace_data['memory']['stack'].append({
                            'name': var_name,
                            'value': heap_id,
                            'type': 'reference'
                        })
                        
                        # 在堆中添加实际对象
                        trace_data['memory']['heap'].append({
                            'id': heap_id,
                            'value': var_value
                        })
            
            execution_trace.append(trace_data)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            continue
    
    return execution_trace

def analyze_python_structure(code):
    """分析Python代码结构，使用AST模块识别函数、类、循环等"""
    import ast
    
    structure = {
        "functions": [],
        "classes": [],
        "loops": [],
        "conditionals": []
    }
    
    try:
        # 解析代码为AST
        tree = ast.parse(code)
        
        # 定义AST访问器来收集代码结构信息
        class StructureVisitor(ast.NodeVisitor):
            def __init__(self):
                self.functions = []
                self.classes = []
                self.loops = []
                self.conditionals = []
                self.current_line = 0
            
            def visit_FunctionDef(self, node):
                self.functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args]
                })
                self.generic_visit(node)
            
            def visit_ClassDef(self, node):
                self.classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "bases": [base.id if isinstance(base, ast.Name) else "..." for base in node.bases]
                })
                self.generic_visit(node)
            
            def visit_For(self, node):
                self.loops.append({
                    "type": "for",
                    "line": node.lineno,
                    "target": ast.unparse(node.target) if hasattr(ast, 'unparse') else "..."
                })
                self.generic_visit(node)
            
            def visit_While(self, node):
                self.loops.append({
                    "type": "while",
                    "line": node.lineno
                })
                self.generic_visit(node)
            
            def visit_If(self, node):
                self.conditionals.append({
                    "type": "if",
                    "line": node.lineno
                })
                # 递归访问子节点，包括else分支
                self.generic_visit(node)
        
        # 执行访问器
        visitor = StructureVisitor()
        visitor.visit(tree)
        
        # 将收集到的信息添加到结构中
        structure["functions"] = visitor.functions
        structure["classes"] = visitor.classes
        structure["loops"] = visitor.loops
        structure["conditionals"] = visitor.conditionals
        
    except SyntaxError as e:
        # 如果代码有语法错误，回退到简单的行分析
        lines = code.split('\n')
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith('def '):
                function_name = line_stripped[4:].split('(')[0]
                structure["functions"].append({
                    "name": function_name,
                    "line": i+1
                })
            elif line_stripped.startswith('class '):
                class_name = line_stripped[6:].split('(')[0].split(':')[0]
                structure["classes"].append({
                    "name": class_name,
                    "line": i+1
                })
            elif line_stripped.startswith('for ') or line_stripped.startswith('while '):
                structure["loops"].append({
                    "type": "for" if line_stripped.startswith('for ') else "while",
                    "line": i+1
                })
            elif line_stripped.startswith('if ') or line_stripped.startswith('elif ') or line_stripped.startswith('else:'):
                structure["conditionals"].append({
                    "type": "if" if line_stripped.startswith('if ') else "elif" if line_stripped.startswith('elif ') else "else",
                    "line": i+1
                })
    
    return structure

def analyze_c_code(code):
    # 创建临时文件来存储C代码
    with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as temp_file:
        temp_file.write(code.encode('utf-8'))
        temp_file_path = temp_file.name
    
    try:
        # 使用静态分析来获取代码结构
        code_structure = analyze_c_structure(code)
        
        # 创建一个修改版本的代码，添加跟踪语句
        instrumented_code = instrument_c_code(code)
        with tempfile.NamedTemporaryFile(suffix='.c', delete=False) as instrumented_file:
            instrumented_file.write(instrumented_code.encode('utf-8'))
            instrumented_file_path = instrumented_file.name
        
        # 编译原始C代码（检查语法错误）
        compile_result = subprocess.run(
            ['gcc', '-fsyntax-only', temp_file_path],
            capture_output=True,
            text=True
        )
        
        if compile_result.returncode != 0:
            return {
                "status": "error",
                "error": "Compilation error",
                "stderr": compile_result.stderr
            }
        
        # 编译插桩后的代码
        try:
            executable_path = temp_file_path + '.exe'
            compile_instrumented = subprocess.run(
                ['gcc', instrumented_file_path, '-o', executable_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if compile_instrumented.returncode != 0:
                # 如果插桩代码编译失败，返回原始代码结构
                return {
                    "status": "success",
                    "code_structure": code_structure,
                    "note": "Instrumented code compilation failed, showing static analysis only",
                    "stderr": compile_instrumented.stderr
                }
            
            # 运行编译后的程序
            execution_result = subprocess.run(
                [executable_path],
                capture_output=True,
                text=True,
                timeout=5  # 设置超时，防止无限循环
            )
            
            # 解析输出以获取执行跟踪
            execution_trace = parse_c_execution_trace(execution_result.stdout)
            
            return {
                "status": "success",
                "execution_trace": execution_trace,
                "code_structure": code_structure,
                "stdout": execution_result.stdout,
                "stderr": execution_result.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error", 
                "error": "Code execution timed out",
                "code_structure": code_structure
            }
        except Exception as e:
            # 如果执行失败，至少返回静态分析结果
            return {
                "status": "partial_success",
                "error": f"Execution failed: {str(e)}",
                "code_structure": code_structure
            }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_file_path)
            if 'instrumented_file_path' in locals():
                os.unlink(instrumented_file_path)
            if 'executable_path' in locals() and os.path.exists(executable_path):
                os.unlink(executable_path)
        except:
            pass

def analyze_c_structure(code):
    """分析C代码结构，识别函数、结构体、循环和条件语句等"""
    structure = {
        "functions": [],
        "structs": [],
        "variables": [],
        "loops": [],
        "conditionals": []
    }
    
    lines = code.split('\n')
    # 跟踪大括号以确定代码块
    brace_stack = []
    current_function = None
    in_struct = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 跟踪大括号
        open_braces = line_stripped.count('{')
        close_braces = line_stripped.count('}')
        
        for _ in range(open_braces):
            brace_stack.append(i)
        
        for _ in range(close_braces):
            if brace_stack:
                brace_stack.pop()
        
        # 识别函数定义
        if ')' in line_stripped and '{' in line_stripped and not line_stripped.startswith('#'):
            # 可能是函数定义
            parts = line_stripped.split(')')
            if parts and '(' in parts[0]:
                func_parts = parts[0].split('(')
                if len(func_parts) > 0:
                    # 提取返回类型和函数名
                    func_decl = func_parts[0].split()
                    if len(func_decl) > 0:
                        func_name = func_decl[-1]
                        return_type = ' '.join(func_decl[:-1]) if len(func_decl) > 1 else 'int'
                        
                        # 提取参数
                        params = []
                        if len(func_parts) > 1 and '(' in line_stripped:
                            param_str = line_stripped.split('(')[1].split(')')[0]
                            if param_str.strip() and param_str.strip() != 'void':
                                params = [p.strip() for p in param_str.split(',')]
                        
                        function_info = {
                            "name": func_name,
                            "line": i+1,
                            "return_type": return_type,
                            "params": params
                        }
                        structure["functions"].append(function_info)
                        current_function = func_name
        
        # 识别结构体定义
        if line_stripped.startswith('struct ') and '{' in line_stripped:
            struct_name = line_stripped[7:].split('{')[0].strip()
            structure["structs"].append({
                "name": struct_name,
                "line": i+1
            })
            in_struct = True
        
        # 结构体结束
        if in_struct and '}' in line_stripped and ';' in line_stripped:
            in_struct = False
        
        # 识别全局变量和局部变量
        if ';' in line_stripped and '=' in line_stripped and not line_stripped.startswith('#') and '{' not in line_stripped:
            var_parts = line_stripped.split('=')[0].strip().split()
            if len(var_parts) > 1:
                var_name = var_parts[-1].replace('*', '').strip()
                var_type = ' '.join(var_parts[:-1])
                
                var_info = {
                    "name": var_name,
                    "type": var_type,
                    "line": i+1,
                    "scope": "global" if not current_function else "local"
                }
                structure["variables"].append(var_info)
        
        # 识别循环语句
        if line_stripped.startswith('for ') or line_stripped.startswith('while '):
            loop_type = "for" if line_stripped.startswith('for ') else "while"
            structure["loops"].append({
                "type": loop_type,
                "line": i+1
            })
        
        # 识别条件语句
        if line_stripped.startswith('if ') or line_stripped.startswith('else if ') or line_stripped.startswith('else '):
            cond_type = "if" if line_stripped.startswith('if ') else "else if" if line_stripped.startswith('else if ') else "else"
            structure["conditionals"].append({
                "type": cond_type,
                "line": i+1
            })
    
    return structure

def instrument_c_code(code):
    """向C代码添加跟踪语句，以便跟踪变量和执行流程"""
    # 添加必要的头文件和跟踪函数
    trace_header = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 跟踪函数
void _trace_line(int line_no, const char* func_name) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{}}", line_no, func_name);
    fflush(stdout);
}

// 变量跟踪函数
void _trace_int(int line_no, const char* func_name, const char* var_name, int value) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{\"%s\":\"%d\"}}", 
           line_no, func_name, var_name, value);
    fflush(stdout);
}

void _trace_double(int line_no, const char* func_name, const char* var_name, double value) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{\"%s\":\"%f\"}}", 
           line_no, func_name, var_name, value);
    fflush(stdout);
}

void _trace_char(int line_no, const char* func_name, const char* var_name, char value) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{\"%s\":\"%c\"}}", 
           line_no, func_name, var_name, value);
    fflush(stdout);
}

void _trace_string(int line_no, const char* func_name, const char* var_name, const char* value) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{\"%s\":\"%s\"}}", 
           line_no, func_name, var_name, value ? value : "NULL");
    fflush(stdout);
}

void _trace_pointer(int line_no, const char* func_name, const char* var_name, const void* value) {
    printf("TRACE:{\"line\":%d,\"function\":\"%s\",\"variables\":{\"%s\":\"pointer(%p)\"}}", 
           line_no, func_name, var_name, value);
    fflush(stdout);
}

// 函数调用跟踪
void _trace_call(int line_no, const char* func_name) {
    printf("TRACE:{\"line\":%d,\"event\":\"call\",\"function\":\"%s\"}", 
           line_no, func_name);
    fflush(stdout);
}

// 函数返回跟踪
void _trace_return(int line_no, const char* func_name) {
    printf("TRACE:{\"line\":%d,\"event\":\"return\",\"function\":\"%s\"}", 
           line_no, func_name);
    fflush(stdout);
}
"""
    
    # 解析代码，找出函数和变量
    structure = analyze_c_structure(code)
    
    # 将代码分割成行
    lines = code.split('\n')
    instrumented_lines = []
    
    # 添加跟踪头文件
    instrumented_lines.append(trace_header)
    
    # 当前函数名
    current_function = "global"
    # 跟踪大括号以确定代码块
    brace_stack = []
    # 是否在函数内部
    in_function = False
    
    # 处理每一行代码
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # 跟踪大括号
        open_braces = line_stripped.count('{')
        close_braces = line_stripped.count('}')
        
        # 检测函数定义
        for func in structure["functions"]:
            if func["line"] == i+1:
                current_function = func["name"]
                in_function = True
                # 在函数开始时添加调用跟踪
                instrumented_lines.append(line)
                indent = len(line) - len(line.lstrip())
                trace_call = ' ' * indent + f"_trace_call({i+1}, \"{current_function}\");"
                instrumented_lines.append(trace_call)
                break
        else:
            # 如果不是函数定义行，直接添加
            instrumented_lines.append(line)
        
        # 更新大括号栈
        for _ in range(open_braces):
            brace_stack.append(i)
        
        for _ in range(close_braces):
            if brace_stack:
                brace_stack.pop()
                # 如果大括号栈为空且在函数内，说明函数结束
                if not brace_stack and in_function and '}' in line_stripped:
                    indent = len(line) - len(line.lstrip())
                    trace_return = ' ' * indent + f"_trace_return({i+1}, \"{current_function}\");"
                    instrumented_lines.append(trace_return)
                    in_function = False
                    current_function = "global"
        
        # 在每个语句后添加跟踪调用（简化版，只处理分号结尾的行）
        if ';' in line_stripped and not line_stripped.startswith('#') and in_function:
            indent = len(line) - len(line.lstrip())
            trace_line = ' ' * indent + f"_trace_line({i+1}, \"{current_function}\");"
            instrumented_lines.append(trace_line)
            
            # 尝试跟踪变量（简化版，只处理简单赋值）
            if '=' in line_stripped and not line_stripped.startswith('if') and not line_stripped.startswith('for') and not line_stripped.startswith('while'):
                var_parts = line_stripped.split('=')[0].strip().split()
                if len(var_parts) > 1:
                    var_name = var_parts[-1].replace('*', '').strip()
                    var_type = ' '.join(var_parts[:-1])
                    
                    # 根据变量类型选择跟踪函数
                    if 'int' in var_type:
                        trace_var = ' ' * indent + f"_trace_int({i+1}, \"{current_function}\", \"{var_name}\", {var_name});"
                    elif 'double' in var_type or 'float' in var_type:
                        trace_var = ' ' * indent + f"_trace_double({i+1}, \"{current_function}\", \"{var_name}\", {var_name});"
                    elif 'char' in var_type and '*' in var_type:
                        trace_var = ' ' * indent + f"_trace_string({i+1}, \"{current_function}\", \"{var_name}\", {var_name});"
                    elif 'char' in var_type:
                        trace_var = ' ' * indent + f"_trace_char({i+1}, \"{current_function}\", \"{var_name}\", {var_name});"
                    else:
                        trace_var = ' ' * indent + f"_trace_pointer({i+1}, \"{current_function}\", \"{var_name}\", (void*){var_name});"
                    
                    instrumented_lines.append(trace_var)
    
    # 添加最终跟踪数据输出
    instrumented_lines.append("\nint main_original(int argc, char** argv);");
    instrumented_lines.append("\n// 包装原始main函数");
    instrumented_lines.append("int main(int argc, char** argv) {");
    instrumented_lines.append("    int result = main_original(argc, argv);");
    instrumented_lines.append("    printf(\"TRACE_END\");\n    return result;");
    instrumented_lines.append("}");
    
    # 将原始main函数重命名为main_original
    code_with_main = '\n'.join(instrumented_lines)
    code_with_main = code_with_main.replace("int main(", "int main_original(")
    code_with_main = code_with_main.replace("void main(", "void main_original(")
    
    # 确保只替换第一个main函数
    main_count = code_with_main.count("main_original")
    if main_count > 1:
        # 恢复最后一个替换（我们添加的包装函数）
        last_main_pos = code_with_main.rfind("main_original")
        code_with_main = code_with_main[:last_main_pos] + "main" + code_with_main[last_main_pos+13:]
    
    return code_with_main

def parse_c_execution_trace(output):
    """解析C执行跟踪输出"""
    trace_lines = [line for line in output.split('\n') if line.startswith('TRACE:')]
    execution_trace = []
    call_stack = []
    
    for line in trace_lines:
        try:
            # 提取JSON部分
            json_str = line[len('TRACE:'):]
            trace_data = json.loads(json_str)
            
            # 处理函数调用和返回事件
            if 'event' in trace_data:
                if trace_data['event'] == 'call':
                    call_stack.append(trace_data['function'])
                elif trace_data['event'] == 'return' and call_stack:
                    call_stack.pop()
            
            # 添加调用栈信息
            trace_data['call_stack'] = list(call_stack)
            
            # 增强跟踪数据
            if 'line' in trace_data:
                # 确保变量字段存在
                if 'variables' not in trace_data:
                    trace_data['variables'] = {}
                
                # 添加内存信息
                trace_data['memory'] = {
                    'stack': [],
                    'heap': []
                }
                
                # 处理变量，区分栈和堆
                for var_name, var_value in trace_data['variables'].items():
                    # 简单判断是否为基本类型
                    is_primitive = True
                    if 'pointer' in var_value or 'array' in var_value:
                        is_primitive = False
                    
                    if is_primitive:
                        trace_data['memory']['stack'].append({
                            'name': var_name,
                            'value': var_value,
                            'type': 'primitive'
                        })
                    else:
                        # 为引用类型创建一个唯一ID
                        heap_id = f"id_{len(trace_data['memory']['heap'])}"
                        
                        # 在栈中添加引用
                        trace_data['memory']['stack'].append({
                            'name': var_name,
                            'value': heap_id,
                            'type': 'reference'
                        })
                        
                        # 在堆中添加实际对象
                        trace_data['memory']['heap'].append({
                            'id': heap_id,
                            'value': var_value
                        })
            
            execution_trace.append(trace_data)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            continue
    
    return execution_trace

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)