
import os
import re
import sys

# Configuration
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/nebulus_gantry'))
BACKEND_ROOT = os.path.join(PROJECT_ROOT, 'routers')
FRONTEND_ROOT = os.path.join(PROJECT_ROOT, 'public')  # Legacy JS location

# Architecture Rules
RULES = [
    {
        "id": "PY_NO_PRINT",
        "desc": "Use logger instead of print()",
        "pattern": r"^\s*print\(",
        "files": r"\.py$",
        "exclude": ["cli.py", "scan_anti_patterns.py"]
    },
    {
        "id": "PY_SQL_IN_ROUTES",
        "desc": "No Raw SQL in Routers (Use ORM or Service)",
        "pattern": r"(execute\(\s*[\"']SELECT|execute\(\s*[\"']INSERT|execute\(\s*[\"']UPDATE)",
        "files": r"\.py$",
        "path_filter": lambda p: "routers" in p
    },
    {
        "id": "JS_NO_VAR",
        "desc": "Use const/let instead of var",
        "pattern": r"\bvar\s+",
        "files": r"\.js$"
    },
    {
        "id": "JS_QUERY_SELECTOR_GLOBAL",
        "desc": "Direct DOM access outside of Component Class (Heuristic)",
        "pattern": r"document\.querySelector\(",
        "files": r"\.js$",
        # Crude heuristic: if it's in a file not named Component or in legacy public/script.js
        "path_filter": lambda p: "public/script.js" in p
    },
    {
        "id": "JS_GET_ELEMENT_BY_ID_GLOBAL",
        "desc": "Direct DOM access outside of Component Class (Heuristic)",
        "pattern": r"document\.getElementById\(",
        "files": r"\.js$",
        "path_filter": lambda p: "public/script.js" in p
    }
]


def scan_file(filepath):
    violations = []

    # Check if file matches any rule before opening
    relevant_rules = []
    for rule in RULES:
        if re.search(rule["files"], filepath):
            # check excludes/filters
            if "exclude" in rule and any(ex in filepath for ex in rule["exclude"]):
                continue
            if "path_filter" in rule and not rule["path_filter"](filepath):
                continue
            relevant_rules.append(rule)

    if not relevant_rules:
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line_no, line in enumerate(lines, 1):
                for rule in relevant_rules:
                    if re.search(rule["pattern"], line):
                        violations.append({
                            "rule": rule["id"],
                            "desc": rule["desc"],
                            "file": filepath,
                            "line": line_no,
                            "content": line.strip()
                        })
    except UnicodeDecodeError:
        # distinct error for binary files if they sneak in
        pass
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return violations


def main():
    print(f"Scanning codebase at {PROJECT_ROOT}...")
    all_violations = []

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # Ignore test examples and cache
        if "tests" in root or "__pycache__" in root:
            continue

        for name in files:
            filepath = os.path.join(root, name)
            all_violations.extend(scan_file(filepath))

    if not all_violations:
        print("✅ No anti-patterns found!")
        sys.exit(0)
    else:
        print(f"❌ Found {len(all_violations)} violations:")
        for v in all_violations:
            rel_path = os.path.relpath(v['file'], PROJECT_ROOT)
            print(f"[{v['rule']}] {rel_path}:{v['line']} - {v['content']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
