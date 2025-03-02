import ast

class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.variable_map = {}

    def evaluate(self, node):
        """ 解析 AST 节点，返回 Python 值 """
        if isinstance(node, ast.Constant):
            return node.value  # 解析常量（如 `5`，`"hello"`）

        return None  # 其他情况暂不处理

    def visit_Assign(self, node):
        """处理所有赋值语句"""
        targets = [t.id for t in node.targets if isinstance(t, ast.Name)]

        if not targets:
            return

        var_name = targets[0]

        if isinstance(node.value, ast.List):
            self.variable_map[var_name] = [self.evaluate(elt) for elt in node.value.elts]
            print(f"列表变量: {var_name} = {self.variable_map[var_name]}")

        elif isinstance(node.value, ast.Constant):
            self.variable_map[var_name] = node.value.value
            print(f"赋值变量: {var_name} = {node.value.value}")

        elif isinstance(node.value, ast.Call):
            self._current_assign = var_name
            self.variable_map[var_name] = "FunctionCallResult"
            print(f"赋值变量: {var_name} = FunctionCallResult")

        self.generic_visit(node)
        self._current_assign = None

# 测试代码
code = """
dfs = []
numbers = ["1", "2", "3"]
x = 10
y = "hello"
text = "world"
df = some_function()
"""

analyzer = ImportAnalyzer()
analyzer.visit(ast.parse(code))

# 输出解析结果
print("\n最终变量映射:", analyzer.variable_map)
