import json
import os

def generate_code_map(json_path, out_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write("# Project Code Map\n\n")
        f.write("This document provides an exhaustive map of all source code files, including their purpose, methods, and dependencies.\n\n")

        for relative_path in sorted(data.keys()):
            # skip test files or our own analyzer
            if "tests" in relative_path or "analyzer.py" in relative_path or relative_path.startswith("ui\\web") or "scripts" in relative_path:
                continue

            analysis = data[relative_path]
            if "error" in analysis:
                f.write(f"## 📄 `{relative_path}`\n\n")
                f.write(f"**Error analyzing file:** {analysis['error']}\n\n")
                continue

            f.write(f"## 📄 `{relative_path}`\n\n")
            
            # Purpose
            docstring = analysis.get('docstring')
            if docstring:
                f.write(f"**Purpose:**\n```text\n{docstring.strip()}\n```\n\n")
            else:
                f.write("**Purpose:** Core component belonging to its respective subsystem.\n\n")

            # Dependencies
            imports = analysis.get('imports', [])
            if imports:
                f.write("**Dependencies (Imports):**\n")
                # Group standard lib vs internal
                f.write(", ".join(sorted(set(imports))) + "\n\n")

            # Classes
            classes = analysis.get('classes', [])
            if classes:
                f.write("**Classes and Methods:**\n\n")
                for cls in classes:
                    f.write(f"### `class {cls['name']}`\n")
                    if cls['docstring']:
                        f.write(f"> {cls['docstring'].strip().split(repr(chr(10)))[0]}\n\n")
                    
                    if cls['methods']:
                        f.write("| Method | Arguments | Purpose |\n")
                        f.write("|--------|-----------|---------|\n")
                        for method in cls['methods']:
                            args_str = ", ".join(method['args'])
                            m_doc = (method['docstring'] or "Internal logic handler.").split('\n')[0].strip()
                            f.write(f"| `{method['name']}` | `({args_str})` | {m_doc} |\n")
                        f.write("\n")
                    else:
                        f.write("*No explicit methods defined.*\n\n")

            # Functions
            functions = analysis.get('functions', [])
            if functions:
                f.write("**Standalone Functions:**\n\n")
                f.write("| Function | Arguments | Purpose |\n")
                f.write("|----------|-----------|---------|\n")
                for func in functions:
                    args_str = ", ".join(func['args'])
                    f_doc = (func['docstring'] or "Internal utility function.").split('\n')[0].strip()
                    f.write(f"| `{func['name']}` | `({args_str})` | {f_doc} |\n")
                f.write("\n")

            f.write("---\n\n")

if __name__ == '__main__':
    json_path = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime\project_analysis.json"
    out_path = r"D:\AI_Content_Studio\ai_blender_cinematic\antigravity\blender-mcp-server\src\project_kernel_runtime\docs\CODE_MAP.md"
    generate_code_map(json_path, out_path)
    print(f"Generated {out_path}")
