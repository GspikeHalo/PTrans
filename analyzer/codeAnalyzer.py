import ast
import textwrap
import uuid
import json
from variableInfo import VariableInfo
from operatorResult import OperatorResult

class CodeAnalyzerManual:
    def __init__(self):
        self.aliases = {}  # 别名映射表： {别名: 完整原始路径}
        self.current_scope = ["global"]  # 作用域栈（简单实现）
        self.variable_map: {str: VariableInfo} = {}
        self.operators: {str: OperatorResult} = {}
        self.links = {}

        # call 处理器映射，key 为解析后的函数名称，value 为对应的处理器方法
        self.call_handlers = {}
        self.call_handlers["list.append"] = self.handle_append

        self.operators_handlers = {}
        self.operators_handlers["pandas.read_csv"] = self.handle_pandas_read_csv
        self.operators_handlers["pandas.concat"] = self.handle_pandas_concat

    def analyze(self, node):
        """从根节点开始手动遍历 AST"""
        self.visit_node(node)

    def visit_node(self, node):
        """根据节点类型手动选择处理方法"""
        if isinstance(node, ast.Module):
            # 遍历模块内的所有顶级语句
            for stmt in node.body:
                self.visit_node(stmt)
        elif isinstance(node, ast.Import):
            self.handle_import(node)
        elif isinstance(node, ast.ImportFrom):
            self.handle_import_from(node)
        elif isinstance(node, ast.FunctionDef):
            # 进入函数定义，更新作用域，暂时还没有作用
            self.current_scope.append(node.name)
            for stmt in node.body:
                self.visit_node(stmt)
            self.current_scope.pop()
        elif isinstance(node, ast.Assign):
            self.handle_assign(node)
        elif isinstance(node, ast.Expr):
            self.evaluate_expr(node.value)
        # elif isinstance(node, ast.Call):
        #     self.handle_call(node)
        #     # 继续遍历调用节点内部，防止遗漏嵌套调用
        #     for child in ast.iter_child_nodes(node):
        #         self.visit_node(child)
        else:
            # 其他节点，继续手动遍历其所有子节点
            for child in ast.iter_child_nodes(node):
                self.visit_node(child)

    def handle_import(self, node):
        """处理形如 'import pandas as pd' 或 'import numpy, matplotlib' 的语句"""
        for alias in node.names:
            original = alias.name
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                self._add_alias(original, original)

    def handle_import_from(self, node):
        """处理形如 'from pandas import DataFrame as DF' 的语句"""
        module = node.module or ""
        level = node.level  # 处理相对导入，如 from . import submodule
        for alias in node.names:
            original = f"{module}.{alias.name}" if module else alias.name
            if level > 0:
                original = "." * level + original
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                self._add_alias(alias.name, original)

    def _add_alias(self, alias, original):
        """将别名记录到当前作用域（这里只记录全局作用域的别名）"""
        if self.current_scope[-1] == "global":
            self.aliases[alias] = original
        else:
            # 如果需要记录局部作用域的别名，可在此处扩展
            pass

    def handle_assign(self, node):
        value = self.evaluate_expr(node.value)
        # 如果 value 是 operator，则 value 为 operator id
        # 查找 operator 对象，取 returnType 作为变量类型
        var_type = None
        if isinstance(value, OperatorResult) and value.op_id in self.operators:
            # op_obj = self.operators[value]
            # var_type = op_obj.get("returnType", op_obj.get("operatorType"))
            var_type = self.operators[value.op_id].op_type
            value = value.op_id
            print(var_type)

        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if self.current_scope[-1] == "global":
                    self.variable_map[var_name] = VariableInfo(var_name, value, var_type)
            # 可以扩展支持其他类型的赋值目标（例如元组解包等）

    def evaluate_expr(self, node):
        """
        对表达式求值，仅处理以下情况：
          - 常量（数字、字符串等）
          - 简单的二元运算（加、减、乘、除）
          - 列表
        """
        if isinstance(node, ast.Constant):
            return node.value
        # elif isinstance(node, ast.Num):  # 兼容旧版本
        #     return node.n
        # elif isinstance(node, ast.Str):
        #     return node.s
        elif isinstance(node, ast.BinOp):
            left = self.evaluate_expr(node.left)
            right = self.evaluate_expr(node.right)
            if left is None or right is None:
                return None
            if isinstance(node.op, ast.Add):
                return left + right
            elif isinstance(node.op, ast.Sub):
                return left - right
            elif isinstance(node.op, ast.Mult):
                return left * right
            elif isinstance(node.op, ast.Div):
                return left / right
        elif isinstance(node, ast.List):
            return [self.evaluate_expr(element) for element in node.elts]
        elif isinstance(node, ast.Name):
            var_info = self.variable_map.get(node.id, None)
            return var_info.value if var_info is not None else None
        elif isinstance(node, ast.Call):
            return self.handle_call(node)
            # func_name = self.resolve_func_name(node.func)
            # args = [self.evaluate_expr(arg) for arg in node.args]
            # keywords = {kw.arg: self.evaluate_expr(kw.value) for kw in node.keywords}
            # return {"call": {"function": func_name, "args": args, "keywords": keywords}}
        return None

    def resolve_func_name(self, node):
        """
        解析函数调用的函数名。
        支持 Name、Attribute、Subscript 和 Call 形式，例如:
          - my_func -> "my_func"
          - pd.read_csv -> "pd.read_csv"
          - df["col"] -> "df[col]"
          - func()(...) -> 返回 func 的名称
        """
        if isinstance(node, ast.Name):
            # 优先从 variable_map 中获取，如果存在则返回其 type
            if node.id in self.variable_map:
                return self.variable_map[node.id].type
            # 否则使用 aliases 查找
            return self.aliases.get(node.id, node.id)
        elif isinstance(node, ast.Attribute):
            value = self.resolve_func_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Subscript):
            value = self.resolve_func_name(node.value)
            slice_val = None
            if isinstance(node.slice, ast.Constant):
                slice_val = node.slice.value
            elif hasattr(node.slice, "value"):
                slice_val = self.resolve_func_name(node.slice.value) or self.evaluate_expr(node.slice)
            if slice_val is not None:
                return f"{value}[{slice_val}]"
            else:
                return value
        elif isinstance(node, ast.Call):
            return self.handle_call(node)
        return None

    def handle_call(self, node):
        func_name = self.resolve_func_name(node.func)
        if func_name in self.call_handlers:
            result = self.call_handlers[func_name](node)
            return result
        elif func_name in self.operators_handlers:
            operator = self.operators_handlers[func_name](node)
            self.operators[operator.op_id] = operator
            self.create_links_for_call(operator.op_id, node)
            return operator
        else:
            # 默认处理 还没有测试 可以写一个类与operatorResult的类型一致（继承）
            args = [self.evaluate_expr(arg) for arg in node.args]
            keywords = {kw.arg: self.evaluate_expr(kw.value) for kw in node.keywords}
            return {"call": {"function": func_name, "args": args, "keywords": keywords}}

    def handle_pandas_read_csv(self, node) -> OperatorResult:
        """
        自定义处理器：将 pandas.read_csv 转换为 CSVFileScan operator 的 JSON 格式
        规则：
          - 第一个位置参数作为 fileName
          - 关键字参数 encoding、sep、header 分别作为 fileEncoding、customDelimiter、hasHeader
        """
        file_name = self.evaluate_expr(node.args[0]) if node.args else None
        # 默认参数
        file_encoding = "UTF_8"
        custom_delimiter = ","
        has_header = True
        for kw in node.keywords:
            if kw.arg == "encoding":
                file_encoding = self.evaluate_expr(kw.value)
            elif kw.arg == "sep":
                custom_delimiter = self.evaluate_expr(kw.value)
            elif kw.arg == "header":
                header_val = self.evaluate_expr(kw.value)
                # 在 pandas 中 header=None 表示没有 header
                has_header = header_val is not None
        operator = {
            "operatorID": f"CSVFileScan-operator-{uuid.uuid4()}",
            "operatorType": "CSVFileScan",
            "operatorVersion": "N/A",
            "operatorProperties": {
                "fileEncoding": file_encoding,
                "customDelimiter": custom_delimiter,
                "hasHeader": has_header,
                "fileName": file_name # 这里是路劲，路径当前有问题
            },
            "inputPorts": [],
            "outputPorts": [
                {
                    "portID": "output-0",
                    "displayName": "",
                    "allowMultiInputs": False,
                    "isDynamicPort": False
                }
            ],
            "showAdvanced": False,
            "isDisabled": False,
            "customDisplayName": file_name,
            "dynamicInputPorts": False,
            "dynamicOutputPorts": False
        }
        return OperatorResult(operator["operatorID"], "pandas.DataFrame", operator)

    def handle_append(self, node):
        """
        自定义处理器：处理列表的 append 调用。
        规则：
          - 获取调用对象（例如变量 a），检查该变量是否存在且为列表（通过 VariableInfo.value）
          - 解析第一个参数的值，并追加到该列表中
          - 返回 None，模拟列表 append 的返回值
        """
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "append"):
            return None
        target_node = node.func.value
        if isinstance(target_node, ast.Name):
            var_name = target_node.id
            var_info = self.variable_map.get(var_name, None)
            if var_info is not None and isinstance(var_info.value, list):
                if node.args:
                    append_value = self.evaluate_expr(node.args[0])
                    var_info.value.append(append_value)
        return None

    def handle_pandas_concat(self, node) -> OperatorResult:
        """
        自定义处理器：将 pandas.concat 转换为 Concat operator 的 JSON 格式
        规则：
          - 第一个位置参数应为一个列表（包含待连接对象），记录到 operatorProperties 中
          - 关键字参数如 axis、ignore_index 等也记录到 operatorProperties 中
        """
        # # 取第一个位置参数作为待连接对象列表
        concat_list = self.evaluate_expr(node.args[0]) if node.args else []
        operator = {
            "operatorID": f"Union-operator-{uuid.uuid4()}",
            "operatorType": "Union",
            "operatorVersion": "N/A",
            "operatorProperties": {},
            "inputPorts": [
                {
                    "portID": "input-0",
                    "displayName": "",
                    "allowMultiInputs": True,
                    "isDynamicPort": False,
                    "dependencies": []
                }
            ],
            "outputPorts": [
                {
                    "portID": "output-0",
                    "displayName": "",
                    "allowMultiInputs": False,
                    "isDynamicPort": False
                }
            ],
            "showAdvanced": False,
            "isDisabled": False,
            "customDisplayName": "Union",
            "dynamicInputPorts": False,
            "dynamicOutputPorts": False
        }
        return OperatorResult(operator["operatorID"], "pandas.DataFrame", operator)

    def create_links_for_call(self, current_operator_id, call_node):
        """
        检查 call_node 中的参数（位置参数和关键字参数），
        如果其中包含 operator（即其值为已生成 operator 的 id），
        为每个参数生成一个 link：源为参数中的 operator，目标为 current_operator_id，
        默认端口为 source: output-0，target: input-0。
        """
        # 收集参数中的 operator id
        operator_ids = []
        for arg in call_node.args:
            val = self.evaluate_expr(arg)
            operator_ids.extend(self.collect_operator_ids(val))
        for kw in call_node.keywords:
            val = self.evaluate_expr(kw.value)
            operator_ids.extend(self.collect_operator_ids(val))
        # 去重后生成 link
        for src_id in set(operator_ids):
            self.create_link(src_id, current_operator_id)

    def collect_operator_ids(self, value):
        result = []
        if isinstance(value, list):
            for item in value:
                result.extend(self.collect_operator_ids(item))
        elif isinstance(value, str) and value in self.operators:
            result.append(value)
        elif isinstance(value, VariableInfo):
            if isinstance(value.value, list):
                result.extend(self.collect_operator_ids(value.value))
            elif isinstance(value.value, str) and value.value in self.operators:
                result.append(value.value)
        return result

    def create_link(self, source_op, target_op, source_port="output-0", target_port="input-0"):
        """创建一个 link 对象，并保存到 self.links 字典中"""
        linkID = str(uuid.uuid4())
        link = {
            "linkID": linkID,
            "source": {
                "operatorID": source_op,
                "portID": source_port
            },
            "target": {
                "operatorID": target_op,
                "portID": target_port
            }
        }
        self.links[linkID] = link


# 测试代码
if __name__ == '__main__':
    test_code = textwrap.dedent("""
        import pandas as pd

        a = 123
        b = "string"
        
        c = a
        d = []
        d.append(a)
        d.append(321)
        

        # 模拟 CSVFileScan 生成
        res_csv1 = pd.read_csv("data1.csv", encoding="UTF_8", sep=",", header=0)
        res_csv2 = pd.read_csv("data2.csv", encoding="UTF_8", sep=",", header=0)

        # 生成 concat 操作，其输入为两个 CSVFileScan 的 id
        df_list = [res_csv1, res_csv2]
        res_concat = pd.concat(df_list, axis=0, ignore_index=True)
    """)

    tree = ast.parse(test_code)
    analyzer = CodeAnalyzerManual()
    analyzer.analyze(tree)

    print("全局别名映射：")
    for alias, original in analyzer.aliases.items():
        print(f"{alias} -> {original}")

    print("\n全局变量映射：")
    for var, val in analyzer.variable_map.items():
        print(f"{var} -> {val.name}, {val.type}, {val.value}")

    print("\n生成的 Operators：")
    for op_id, op in analyzer.operators.items():
        print(op.op_id, op.op_type, op.op_content)

    print("\n生成的 Links：")
    for link_id, link in analyzer.links.items():
        print(link)

    # 构造 workflow JSON 结构
    workflow = {
        "operators": [op.op_content for op in analyzer.operators.values()],
        "operatorPositions": {op_id: {"x": 0, "y": 0} for op_id in analyzer.operators},
        "links": list(analyzer.links.values()),
        "commentBoxes": [],
        "settings": {
            "dataTransferBatchSize": 400
        }
    }

    with open("workflow.json", "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2)

    # print(json.dumps(workflow, indent=2))
