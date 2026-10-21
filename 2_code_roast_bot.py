"""
Code Roast & Review Bot
-----------------------
Static analysis with Python's `ast` module + a sense of humour. No API needed.

  CLI :  python 2_code_roast_bot.py your_file.py
  Web :  streamlit run 2_code_roast_bot.py

Install (web only):  pip install streamlit
"""
import ast
import random
import sys
from dataclasses import dataclass

ROASTS = {
    "module_doc": ["No module docstring. Mystery box energy.", "Opening this file is like opening a surprise parcel."],
    "no_doc": ["has no docstring. Bold of you to assume people can read minds.",
               "has no docstring. Future you will hate present you."],
    "long_func": ["is a novel, not a function. Split it up!", "is so long it needs a table of contents."],
    "many_args": ["takes way too many arguments. Is it a function or a questionnaire?",
                  "has more parameters than my last exam had questions."],
    "mutable_default": ["uses a mutable default argument. That's a classic bug waiting to bite.",
                        "has a mutable default. The list remembers everything. Always."],
    "deep_nesting": ["is nested deeper than an Inception dream.", "has so many indents it needs a ladder."],
    "bare_except": ["uses a bare `except:`. It catches everything, even Ctrl+C. Chaos!",
                    "swallows every error silently. Bugs love this one trick."],
    "unused_var": ["assigns a variable that is never used. Hoarding variables, are we?",
                   "has a variable that's just taking up space."],
    "star_import": ["uses `import *`. Now nobody knows where anything comes from.",
                    "star import detected. Namespace pollution is not a hobby."],
}


@dataclass
class Issue:
    line: int
    kind: str
    detail: str
    penalty: int

    def roast(self) -> str:
        return f"{self.detail} {random.choice(ROASTS[self.kind])}"


def nesting_depth(node: ast.AST, depth: int = 0) -> int:
    block = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)
    deepest = depth
    for child in ast.iter_child_nodes(node):
        d = depth + 1 if isinstance(child, block) else depth
        deepest = max(deepest, nesting_depth(child, d))
    return deepest


def analyze(source: str):
    tree = ast.parse(source)
    issues = []

    if not ast.get_docstring(tree):
        issues.append(Issue(1, "module_doc", "Module:", 3))

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and any(a.name == "*" for a in node.names):
            issues.append(Issue(node.lineno, "star_import", f"`from {node.module} import *`", 5))

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append(Issue(node.lineno, "bare_except", "Exception handler:", 8))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if not ast.get_docstring(node):
                issues.append(Issue(node.lineno, "no_doc", f"`{name}`", 2))

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            length = (node.end_lineno or node.lineno) - node.lineno + 1
            if length > 40:
                issues.append(Issue(node.lineno, "long_func", f"`{node.name}` ({length} lines)", 6))

            n_args = len(node.args.args) + len(node.args.kwonlyargs)
            if n_args > 5:
                issues.append(Issue(node.lineno, "many_args", f"`{node.name}` ({n_args} args)", 4))

            if any(isinstance(d, (ast.List, ast.Dict, ast.Set)) for d in node.args.defaults + node.args.kw_defaults if d):
                issues.append(Issue(node.lineno, "mutable_default", f"`{node.name}`", 7))

            depth = nesting_depth(node)
            if depth > 3:
                issues.append(Issue(node.lineno, "deep_nesting", f"`{node.name}` (depth {depth})", 5))

            stores = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            loads = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            for var in sorted(stores - loads):
                if not var.startswith("_"):
                    issues.append(Issue(node.lineno, "unused_var", f"`{node.name}` -> `{var}`", 2))

    issues.sort(key=lambda i: i.line)
    score = max(0, 100 - sum(i.penalty for i in issues))
    return issues, score


def verdict(score: int) -> str:
    if score >= 90:
        return "🏆 Chef's kiss. Suspiciously clean."
    if score >= 75:
        return "👍 Pretty decent. A few spicy bits."
    if score >= 50:
        return "😬 It works, but it's held together by hope."
    return "🔥 This code needs an intervention."


def run_cli(path: str) -> None:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    try:
        issues, score = analyze(src)
    except SyntaxError as e:
        print(f"💀 Can't even parse this: {e}")
        return
    print(f"\n=== Code Health Score: {score}/100 ===\n{verdict(score)}\n")
    for i in issues:
        print(f"  line {i.line:>4}: {i.roast()}")
    if not issues:
        print("  Nothing to roast. I'm a little disappointed.")


def run_web() -> None:
    import streamlit as st

    st.set_page_config(page_title="Code Roast Bot", page_icon="🔥")
    st.title("🔥 Code Roast & Review Bot")
    up = st.file_uploader("Upload a .py file", type=["py"])
    pasted = st.text_area("...or paste code here", height=250)
    src = up.read().decode("utf-8") if up else pasted

    if st.button("Roast me", type="primary") and src.strip():
        try:
            issues, score = analyze(src)
        except SyntaxError as e:
            st.error(f"💀 Syntax error, can't analyze: {e}")
            return
        st.metric("Code Health Score", f"{score}/100")
        st.progress(score / 100)
        st.subheader(verdict(score))
        for i in issues:
            st.warning(f"**Line {i.line}** — {i.roast()}")
        if not issues:
            st.success("Nothing to roast. I'm a little disappointed.")
        else:
            st.caption(f"{len(issues)} issue(s) found.")


def _in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if _in_streamlit():
    run_web()
elif __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 2_code_roast_bot.py your_file.py   (or: streamlit run 2_code_roast_bot.py)")
    else:
        run_cli(sys.argv[1])
