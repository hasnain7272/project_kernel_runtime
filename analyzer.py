import ast
import os
import json
from pathlib import Path

def analyze_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content, filename=filepath)
    except Exception as e:
        return {'error': str(e)}

    analysis = {
        'path': filepath,
        'docstring': ast.get_docstring(tree),
        'imports': [],
        'classes': [],
        'functions': []
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                analysis['imports'].append(n.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for n in node.names:
                analysis['imports'].append(f"{module}.{n.name}")
        elif isinstance(node, ast.ClassDef):
            class_info = {
                'name': node.name,
                'docstring': ast.get_docstring(node),
                'methods': []
            }
            for cls_node in node.body:
                if isinstance(cls_node, ast.FunctionDef) or isinstance(cls_node, ast.AsyncFunctionDef):
                    args = [a.arg for a in getattr(cls_node.args, 'args', [])]
                    class_info['methods'].append({
                        'name': cls_node.name,
                        'args': args,
                        'docstring': ast.get_docstring(cls_node)
                    })
            analysis['classes'].append(class_info)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            args = [a.arg for a in getattr(node.args, 'args', [])]
            analysis['functions'].append({
                'name': node.name,
                'args': args,
                'docstring': ast.get_docstring(node)
            })

    return analysis

def scan_directory(directory):
    directory_path = Path(directory)
    results = {}
    for py_file in directory_path.rglob('*.py'):
        # skip virtual envs, pycache, etc if any inside
        if 'node_modules' in py_file.parts or '.venv' in py_file.parts:
            continue
        rel_path = str(py_file.relative_to(directory_path)).replace('\\', '/')
        results[rel_path] = analyze_file(str(py_file))
    return results

if __name__ == '__main__':
    src_dir = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime"
    out_file = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime\project_analysis.json"
    
    analysis_data = scan_directory(src_dir)
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, indent=2)
    print(f"Generated {out_file}")
