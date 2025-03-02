import ast
import textwrap

class CodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.aliases = {}  # 别名映射表结构: {别名: 完整原始路径}
        self.current_scope = ["global"]  # 作用域栈（简单实现）

        self.variable_map = {}
        self._current_assign = None

    # ==================== Import Related =======================
    # 处理常规import语句
    def visit_Import(self, node):
        for alias in node.names:
            original = alias.name
            # 处理 "import pandas as pd"
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                # 处理 "import pandas"（无别名时，原名称也是别名）
                self._add_alias(original, original)
        self.generic_visit(node)

    # 处理from...import语句
    def visit_ImportFrom(self, node):
        module = node.module or ""
        level = node.level  # 处理相对导入（如from . import submodule）

        for alias in node.names:
            original = f"{module}.{alias.name}" if module else alias.name
            # 处理相对导入路径
            if level > 0:
                original = "." * level + original

            # 处理 "from pandas import read_csv as rc"
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                self._add_alias(alias.name, original)
        self.generic_visit(node)

    def _add_alias(self, alias, original):
        """记录别名到当前作用域"""
        # 简单实现：全局作用域存储
        if self.current_scope[-1] == "global":
            self.aliases[alias] = original
        else:
            pass

# ==================== Assign Related =======================
    def evaluate(self, node):
        """ 解析 AST 节点，返回 Python 值 """
        if isinstance(node, ast.Constant):
            return node.value

        return None

    def visit_Assign(self, node):
        """处理所有赋值语句"""
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]

        if not targets:
            return

        var_name = targets[0]

        if isinstance(node.value, ast.List):
            self.variable_map[var_name] = [self.evaluate(elt) for elt in node.value.elts]

        elif isinstance(node.value, ast.Constant):
            self.variable_map[var_name] = node.value.value

        elif isinstance(node.value, ast.Call):
            self._current_assign = var_name # ？？？

        self.generic_visit(node)
        self._current_assign = None

# ==================== Call Related =======================
    def visit_Call(self, node):
        pass


