from pathlib import Path
from tree_sitter import Language, Parser, Node
from collections import defaultdict
import asyncio
import structlog
from core.lancedb_client import add_memory

logger = structlog.get_logger()

# Load Tree-sitter Python language
PY_LANGUAGE = Language('build/my-languages.so', 'python')
parser = Parser()
parser.set_language(PY_LANGUAGE)

# Global graph structures (in-memory for speed, can be persisted later)
function_graph = defaultdict(set)          # caller_function -> set of callee_functions
file_functions = defaultdict(list)         # file_path -> list of function names
function_locations = {}                    # function_name -> (file_path, start_byte, end_byte)

async def parse_file(file_path: Path) -> tuple[Node, str]:
    try:
        code = await asyncio.to_thread(file_path.read_text, encoding="utf-8")
        tree = await asyncio.to_thread(parser.parse, bytes(code, "utf8"))
        return tree.root_node, code
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return None, ""

def extract_functions_and_calls(root: Node, code: str):
    funcs = {}
    calls = defaultdict(set)

    def visit(node: Node):
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte]
                funcs[name] = node
                function_locations[name] = (str(node.start_point), str(node.end_point))
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node and func_node.type in ("identifier", "attribute"):
                # Simple case - direct function call
                call_name = code[func_node.start_byte:func_node.end_byte]
                calls[call_name].add(call_name)  # self-reference for now
        for child in node.children:
            visit(child)

    visit(root)
    return funcs, calls

async def build_graph(repo_path: str):
    global function_graph, file_functions, function_locations
    function_graph.clear()
    file_functions.clear()
    function_locations.clear()

    repo_root = Path(repo_path)
    py_files = list(repo_root.rglob("*.py"))

    for file_path in py_files:
        rel_path = file_path.relative_to(repo_root).as_posix()
        root, code = await parse_file(file_path)
        if not root:
            continue
        funcs, calls = await asyncio.to_thread(extract_functions_and_calls, root, code)
        file_functions[rel_path] = list(funcs.keys())
        for caller, callees in calls.items():
            function_graph[caller].update(callees)

        # Embed function nodes for semantic search
        for func_name, node in funcs.items():
            func_code = code[node.start_byte:node.end_byte]
            await add_memory(repo_root.name, f"Function {func_name} in {rel_path}:\n{func_code}")

    logger.info(f"Repo graph built: {len(function_graph)} functions, {len(file_functions)} files")

async def get_impacted_functions(changed_funcs: list[str]) -> set[str]:
    impacted = set()
    visited = set()
    stack = list(changed_funcs)

    while stack:
        func = stack.pop()
        if func in visited:
            continue
        visited.add(func)
        impacted.add(func)
        # Find callers (reverse lookup)
        for caller, callees in function_graph.items():
            if func in callees and caller not in visited:
                stack.append(caller)

    return impacted
