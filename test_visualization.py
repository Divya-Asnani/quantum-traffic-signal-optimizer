import sys
import json
from pathlib import Path
import ast

file_path = Path("app/streamlit_app.py")
source = file_path.read_text(encoding="utf-8")

tree = ast.parse(source)

render_func = None

for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == "render_intersection":
        render_func = node
        break

if render_func is None:
    raise RuntimeError("render_intersection function not found")

module = ast.Module(
    body=[render_func],
    type_ignores=[]
)

compiled = compile(module, str(file_path), "exec")

namespace = {
    "json": json
}

exec(compiled, namespace)

render_intersection = namespace["render_intersection"]

traffic = {
    "North": 70.75,
    "East": 30.17,
    "South": 28.64,
    "West": 20.61
}

timing = {
    "North": 10,
    "East": 10,
    "South": 20,
    "West": 20
}

html = render_intersection(
    traffic_demand=traffic,
    signal_timing=timing,
    mode="populated"
)

print("HTML LENGTH:", len(html))
print("HAS VEHICLES:", "vehicle" in html.lower())
print("HAS TRAFFIC:", "traffic" in html.lower())
print("HAS INTERSECTION:", "intersection" in html.lower())

output_file = Path("results/test_intersection.html")
output_file.write_text(html, encoding="utf-8")

print("HTML FILE CREATED:")
print(output_file)