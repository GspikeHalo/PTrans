# import ast
#
# class ImportAnalyzer(ast.NodeVisitor):
#     def __init__(self):
#         self.variable_map = {}
#
#     def evaluate(self, node):
#         """ 解析 AST 节点，返回 Python 值 """
#         if isinstance(node, ast.Constant):
#             return node.value  # 解析常量（如 `5`，`"hello"`）
#
#         return None  # 其他情况暂不处理
#
#     def visit_Assign(self, node):
#         """处理所有赋值语句"""
#         targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
#
#         if not targets:
#             return
#
#         var_name = targets[0]
#
#         if isinstance(node.value, ast.List):
#             self.variable_map[var_name] = [self.evaluate(elt) for elt in node.value.elts]
#             print(f"列表变量: {var_name} = {self.variable_map[var_name]}")
#
#         elif isinstance(node.value, ast.Constant):
#             self.variable_map[var_name] = node.value.value
#             print(f"赋值变量: {var_name} = {node.value.value}")
#
#         elif isinstance(node.value, ast.Call):
#             self._current_assign = var_name
#             self.variable_map[var_name] = "FunctionCallResult"
#             print(f"赋值变量: {var_name} = FunctionCallResult")
#
#         self.generic_visit(node)
#         self._current_assign = None
#
# # 测试代码
# code = """
# dfs = []
# numbers = ["1", "2", "3"]
# x = 10
# y = "hello"
# text = "world"
# df = some_function()
# """
#
# analyzer = ImportAnalyzer()
# analyzer.visit(ast.parse(code))
#
# # 输出解析结果
# print("\n最终变量映射:", analyzer.variable_map)

# import ast
# import textwrap
# import uuid
# import json
#
#
# class VariableInfo:
#     def __init__(self, name, value, var_type=None):
#         self.name = name
#         self.value = value
#         if var_type is not None:
#             self.type = var_type
#         else:
#             self.type = self.get_variable_type(value)
#
#     def get_variable_type(self, value):
#         # 如果不是 operator，则根据内置类型判断
#         if isinstance(value, str):
#             return "string"
#         if isinstance(value, int):
#             return "int"
#         if isinstance(value, float):
#             return "float"
#         if isinstance(value, bool):
#             return "bool"
#         if isinstance(value, list):
#             return "list"
#         if value is None:
#             return "None"
#         return type(value).__name__
#
#     def to_dict(self):
#         return {
#             "name": self.name,
#             "type": self.type,
#             "value": self.value
#         }
#
#
# class CodeAnalyzerManual:
#     def __init__(self):
#         self.aliases = {}  # {alias: original}
#         self.current_scope = ["global"]
#         # 变量保存为 {变量名: VariableInfo}
#         self.variable_map = {}
#         # operator 用字典保存，key 为 operatorID
#         self.operators = {}
#         # 保存生成的 link，key 为 linkID
#         self.links = {}
#         # call 处理器映射
#         self.call_handlers = {}
#         self.call_handlers["pandas.read_csv"] = self.handle_pandas_read_csv
#         self.call_handlers["pandas.concat"] = self.handle_pandas_concat
#
#     def analyze(self, node):
#         self.visit_node(node)
#
#     def visit_node(self, node):
#         if isinstance(node, ast.Module):
#             for stmt in node.body:
#                 self.visit_node(stmt)
#         elif isinstance(node, ast.Expr):
#             self.evaluate_expr(node.value)
#         elif isinstance(node, ast.Import):
#             self.handle_import(node)
#         elif isinstance(node, ast.ImportFrom):
#             self.handle_import_from(node)
#         elif isinstance(node, ast.FunctionDef):
#             self.current_scope.append(node.name)
#             for stmt in node.body:
#                 self.visit_node(stmt)
#             self.current_scope.pop()
#         elif isinstance(node, ast.Assign):
#             self.handle_assign(node)
#         else:
#             for child in ast.iter_child_nodes(node):
#                 self.visit_node(child)
#
#     def handle_import(self, node):
#         for alias in node.names:
#             original = alias.name
#             if alias.asname:
#                 self._add_alias(alias.asname, original)
#             else:
#                 self._add_alias(original, original)
#
#     def handle_import_from(self, node):
#         module = node.module or ""
#         level = node.level
#         for alias in node.names:
#             original = f"{module}.{alias.name}" if module else alias.name
#             if level > 0:
#                 original = "." * level + original
#             if alias.asname:
#                 self._add_alias(alias.asname, original)
#             else:
#                 self._add_alias(alias.name, original)
#
#     def handle_assign(self, node):
#         value = self.evaluate_expr(node.value)
#         # 如果 value 是 operator，则 value 为 operator id
#         # 查找 operator 对象，取 returnType 作为变量类型
#         var_type = None
#         if isinstance(value, str) and value in self.operators:
#             op_obj = self.operators[value]
#             var_type = op_obj.get("returnType", op_obj.get("operatorType"))
#         for target in node.targets:
#             if isinstance(target, ast.Name):
#                 var_name = target.id
#                 if self.current_scope[-1] == "global":
#                     self.variable_map[var_name] = VariableInfo(var_name, value, var_type)
#
#     def evaluate_expr(self, node):
#         if isinstance(node, ast.Constant):
#             return node.value
#         elif isinstance(node, ast.Num):
#             return node.n
#         elif isinstance(node, ast.Str):
#             return node.s
#         elif isinstance(node, ast.BinOp):
#             left = self.evaluate_expr(node.left)
#             right = self.evaluate_expr(node.right)
#             if left is None or right is None:
#                 return None
#             if isinstance(node.op, ast.Add):
#                 return left + right
#             elif isinstance(node.op, ast.Sub):
#                 return left - right
#             elif isinstance(node.op, ast.Mult):
#                 return left * right
#             elif isinstance(node.op, ast.Div):
#                 return left / right
#         elif isinstance(node, ast.List):
#             return [self.evaluate_expr(element) for element in node.elts]
#         elif isinstance(node, ast.Call):
#             return self.handle_call(node)
#         elif isinstance(node, ast.Name):
#             var_info = self.variable_map.get(node.id, None)
#             if var_info:
#                 return var_info.value
#             return None
#         return None
#
#     def handle_call(self, node):
#         if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
#             return self.handle_append(node)
#         func_name = self.resolve_func_name(node.func)
#         if func_name in self.call_handlers:
#             operator = self.call_handlers[func_name](node)
#             self.operators[operator["operatorID"]] = operator
#             self.create_links_for_call(operator["operatorID"], node)
#             return operator["operatorID"]
#         else:
#             args = [self.evaluate_expr(arg) for arg in node.args]
#             keywords = {kw.arg: self.evaluate_expr(kw.value) for kw in node.keywords}
#             return {"call": {"function": func_name, "args": args, "keywords": keywords}}
#
#     def handle_append(self, node):
#         if not (isinstance(node.func, ast.Attribute) and node.func.attr == "append"):
#             return None
#         target_node = node.func.value
#         if isinstance(target_node, ast.Name):
#             var_name = target_node.id
#             var_info = self.variable_map.get(var_name, None)
#             if var_info and isinstance(var_info.value, list):
#                 if node.args:
#                     append_value = self.evaluate_expr(node.args[0])
#                     var_info.value.append(append_value)
#         return None
#
#     def handle_pandas_read_csv(self, node):
#         file_name = self.evaluate_expr(node.args[0]) if node.args else None
#         file_encoding = "UTF_8"
#         custom_delimiter = ","
#         has_header = True
#         for kw in node.keywords:
#             if kw.arg == "encoding":
#                 file_encoding = self.evaluate_expr(kw.value)
#             elif kw.arg == "sep":
#                 custom_delimiter = self.evaluate_expr(kw.value)
#             elif kw.arg == "header":
#                 header_val = self.evaluate_expr(kw.value)
#                 has_header = header_val is not None
#         operator = {
#             "operatorID": f"CSVFileScan-operator-{uuid.uuid4()}",
#             "operatorType": "CSVFileScan",
#             "operatorVersion": "N/A",
#             "operatorProperties": {
#                 "fileEncoding": file_encoding,
#                 "customDelimiter": custom_delimiter,
#                 "hasHeader": has_header,
#                 "fileName": file_name
#             },
#             "inputPorts": [],
#             "outputPorts": [
#                 {
#                     "portID": "output-0",
#                     "displayName": "",
#                     "allowMultiInputs": False,
#                     "isDynamicPort": False
#                 }
#             ],
#             "showAdvanced": False,
#             "isDisabled": False,
#             "customDisplayName": "CSVFileScan",
#             "dynamicInputPorts": False,
#             "dynamicOutputPorts": False,
#             # 指定返回类型为 pandas.DataFrame
#             "returnType": "pandas.DataFrame"
#         }
#         return operator
#
#     def handle_pandas_concat(self, node):
#         concat_list = self.evaluate_expr(node.args[0]) if node.args else []
#         axis = 0
#         ignore_index = False
#         for kw in node.keywords:
#             if kw.arg == "axis":
#                 axis = self.evaluate_expr(kw.value)
#             elif kw.arg == "ignore_index":
#                 ignore_index = self.evaluate_expr(kw.value)
#         operator = {
#             "operatorID": f"Concat-operator-{uuid.uuid4()}",
#             "operatorType": "Concat",
#             "operatorVersion": "N/A",
#             "operatorProperties": {
#                 "concat_list": concat_list,
#                 "axis": axis,
#                 "ignore_index": ignore_index
#             },
#             "inputPorts": [
#                 {
#                     "portID": "input-0",
#                     "displayName": "",
#                     "allowMultiInputs": True,
#                     "isDynamicPort": False,
#                     "dependencies": []
#                 }
#             ],
#             "outputPorts": [
#                 {
#                     "portID": "output-0",
#                     "displayName": "",
#                     "allowMultiInputs": False,
#                     "isDynamicPort": False
#                 }
#             ],
#             "showAdvanced": False,
#             "isDisabled": False,
#             "customDisplayName": "Concat",
#             "dynamicInputPorts": False,
#             "dynamicOutputPorts": False,
#             # 指定返回类型为 pandas.DataFrame
#             "returnType": "pandas.DataFrame"
#         }
#         return operator
#
#     def create_links_for_call(self, current_operator_id, call_node):
#         operator_ids = []
#         for arg in call_node.args:
#             val = self.evaluate_expr(arg)
#             operator_ids.extend(self.collect_operator_ids(val))
#         for kw in call_node.keywords:
#             val = self.evaluate_expr(kw.value)
#             operator_ids.extend(self.collect_operator_ids(val))
#         for src_id in set(operator_ids):
#             self.create_link(src_id, current_operator_id)
#
#     def collect_operator_ids(self, value):
#         result = []
#         if isinstance(value, list):
#             for item in value:
#                 result.extend(self.collect_operator_ids(item))
#         elif isinstance(value, str) and value in self.operators:
#             result.append(value)
#         return result
#
#     def create_link(self, source_op, target_op, source_port="output-0", target_port="input-0"):
#         linkID = str(uuid.uuid4())
#         link = {
#             "linkID": linkID,
#             "source": {
#                 "operatorID": source_op,
#                 "portID": source_port
#             },
#             "target": {
#                 "operatorID": target_op,
#                 "portID": target_port
#             }
#         }
#         self.links[linkID] = link
#
#     def resolve_func_name(self, node):
#         if isinstance(node, ast.Name):
#             return self.aliases.get(node.id, node.id)
#         elif isinstance(node, ast.Attribute):
#             value = self.resolve_func_name(node.value)
#             return f"{value}.{node.attr}" if value else node.attr
#         return None
#
#     def _add_alias(self, alias, original):
#         if self.current_scope[-1] == "global":
#             self.aliases[alias] = original
#
#
# if __name__ == '__main__':
#     test_code = textwrap.dedent("""
#         import pandas as pd
#
#         a = 123
#         b = "string"
#
#         # 模拟 CSVFileScan 生成
#         res_csv1 = pd.read_csv("data1.csv", encoding="UTF_8", sep=",", header=0)
#         res_csv2 = pd.read_csv("data2.csv", encoding="UTF_8", sep=",", header=0)
#
#         # 生成 concat 操作，其输入为两个 CSVFileScan 的 id
#         df_list = [res_csv1, res_csv2]
#         res_concat = pd.concat(df_list, axis=0, ignore_index=True)
#     """)
#
#     tree = ast.parse(test_code)
#     analyzer = CodeAnalyzerManual()
#     analyzer.analyze(tree)
#
#     print("全局别名映射：")
#     for alias, original in analyzer.aliases.items():
#         print(f"{alias} -> {original}")
#
#     print("\n全局变量映射：")
#     for var, val in analyzer.variable_map.items():
#         print(f"{var} -> {val.name} {val.value} {val.type}")
#
#     print("\n生成的 Operators：")
#     for op_id, op in analyzer.operators.items():
#         print(op)
#
#     print("\n生成的 Links：")
#     for link_id, link in analyzer.links.items():
#         print(link)

import ast
import textwrap
import uuid
import json


class OperatorResult:
    """
    用于存储 operator 调用的返回结果，
    包含 operatorID 和返回类型（op_type），
    方便后续扩展。
    """

    def __init__(self, operator_id, op_type):
        self.operatorID = operator_id
        self.op_type = op_type

    def to_dict(self):
        # 返回存储 operator 的详细内容可以直接取 self.operatorID 对应的 operator 字典
        # 如果需要单独展示返回类型，也可以添加 op_type 信息。
        return {
            "operatorID": self.operatorID,
            "operatorType": self.op_type
        }


class VariableInfo:
    def __init__(self, name, value, var_type=None):
        self.name = name
        self.value = value
        if var_type is not None:
            self.type = var_type
        else:
            self.type = self.get_variable_type(value)

    def get_variable_type(self, value):
        # 如果 value 是 operator 的 id，则默认返回值为 "operator"
        if isinstance(value, str) and (
                value.startswith("CSVFileScan-operator-") or value.startswith("Concat-operator-")):
            return "operator"
        if isinstance(value, str):
            return "string"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, list):
            return "list"
        if value is None:
            return "None"
        return type(value).__name__

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "value": self.value
        }


class CodeAnalyzerManual:
    def __init__(self):
        self.aliases = {}  # {alias: original}
        self.current_scope = ["global"]
        # 变量保存为 {变量名: VariableInfo}
        self.variable_map = {}
        # operator 用字典保存，key 为 operatorID
        self.operators = {}
        # 保存生成的 link，key 为 linkID
        self.links = {}
        # call 处理器映射
        self.call_handlers = {}
        self.call_handlers["pandas.read_csv"] = self.handle_pandas_read_csv
        self.call_handlers["pandas.concat"] = self.handle_pandas_concat

    def analyze(self, node):
        self.visit_node(node)

    def visit_node(self, node):
        if isinstance(node, ast.Module):
            for stmt in node.body:
                self.visit_node(stmt)
        elif isinstance(node, ast.Expr):
            self.evaluate_expr(node.value)
        elif isinstance(node, ast.Import):
            self.handle_import(node)
        elif isinstance(node, ast.ImportFrom):
            self.handle_import_from(node)
        elif isinstance(node, ast.FunctionDef):
            self.current_scope.append(node.name)
            for stmt in node.body:
                self.visit_node(stmt)
            self.current_scope.pop()
        elif isinstance(node, ast.Assign):
            self.handle_assign(node)
        else:
            for child in ast.iter_child_nodes(node):
                self.visit_node(child)

    def handle_import(self, node):
        for alias in node.names:
            original = alias.name
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                self._add_alias(original, original)

    def handle_import_from(self, node):
        module = node.module or ""
        level = node.level
        for alias in node.names:
            original = f"{module}.{alias.name}" if module else alias.name
            if level > 0:
                original = "." * level + original
            if alias.asname:
                self._add_alias(alias.asname, original)
            else:
                self._add_alias(alias.name, original)

    def handle_assign(self, node):
        value = self.evaluate_expr(node.value)
        # 如果 value 是 OperatorResult，则取其 operatorID和 op_type
        var_type = None
        if isinstance(value, OperatorResult):
            var_type = value.op_type
            value = value.operatorID
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if self.current_scope[-1] == "global":
                    self.variable_map[var_name] = VariableInfo(var_name, value, var_type)

    def evaluate_expr(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.Str):
            return node.s
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
        elif isinstance(node, ast.Call):
            return self.handle_call(node)
        elif isinstance(node, ast.Name):
            var_info = self.variable_map.get(node.id, None)
            if var_info:
                return var_info.value
            return None
        return None

    def handle_call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "append":
            return self.handle_append(node)
        func_name = self.resolve_func_name(node.func)
        if func_name in self.call_handlers:
            operator = self.call_handlers[func_name](node)
            self.operators[operator["operatorID"]] = operator
            self.create_links_for_call(operator["operatorID"], node)
            # 返回 OperatorResult，其中包含 operatorID 和类型（这里 operator 中不再包含 returnType 字段）
            # 根据不同处理器，类型可由处理器自己决定
            if func_name == "pandas.read_csv":
                ret_type = "pandas.DataFrame"
            elif func_name == "pandas.concat":
                ret_type = "pandas.DataFrame"
            else:
                ret_type = operator.get("operatorType", "unknown")
            return OperatorResult(operator["operatorID"], ret_type)
        else:
            args = [self.evaluate_expr(arg) for arg in node.args]
            keywords = {kw.arg: self.evaluate_expr(kw.value) for kw in node.keywords}
            return {"call": {"function": func_name, "args": args, "keywords": keywords}}

    def handle_append(self, node):
        if not (isinstance(node.func, ast.Attribute) and node.func.attr == "append"):
            return None
        target_node = node.func.value
        if isinstance(target_node, ast.Name):
            var_name = target_node.id
            var_info = self.variable_map.get(var_name, None)
            if var_info and isinstance(var_info.value, list):
                if node.args:
                    append_value = self.evaluate_expr(node.args[0])
                    var_info.value.append(append_value)
        return None

    def handle_pandas_read_csv(self, node):
        file_name = self.evaluate_expr(node.args[0]) if node.args else None
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
                has_header = header_val is not None
        operator = {
            "operatorID": f"CSVFileScan-operator-{uuid.uuid4()}",
            "operatorType": "CSVFileScan",
            "operatorVersion": "N/A",
            "operatorProperties": {
                "fileEncoding": file_encoding,
                "customDelimiter": custom_delimiter,
                "hasHeader": has_header,
                "fileName": file_name
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
            "customDisplayName": "CSVFileScan",
            "dynamicInputPorts": False,
            "dynamicOutputPorts": False
        }
        return operator

    def handle_pandas_concat(self, node):
        concat_list = self.evaluate_expr(node.args[0]) if node.args else []
        axis = 0
        ignore_index = False
        for kw in node.keywords:
            if kw.arg == "axis":
                axis = self.evaluate_expr(kw.value)
            elif kw.arg == "ignore_index":
                ignore_index = self.evaluate_expr(kw.value)
        operator = {
            "operatorID": f"Concat-operator-{uuid.uuid4()}",
            "operatorType": "Concat",
            "operatorVersion": "N/A",
            "operatorProperties": {
                "concat_list": concat_list,
                "axis": axis,
                "ignore_index": ignore_index
            },
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
            "customDisplayName": "Concat",
            "dynamicInputPorts": False,
            "dynamicOutputPorts": False
        }
        return operator

    def create_links_for_call(self, current_operator_id, call_node):
        operator_ids = []
        for arg in call_node.args:
            val = self.evaluate_expr(arg)
            operator_ids.extend(self.collect_operator_ids(val))
        for kw in call_node.keywords:
            val = self.evaluate_expr(kw.value)
            operator_ids.extend(self.collect_operator_ids(val))
        for src_id in set(operator_ids):
            self.create_link(src_id, current_operator_id)

    def collect_operator_ids(self, value):
        result = []
        if isinstance(value, list):
            for item in value:
                result.extend(self.collect_operator_ids(item))
        elif isinstance(value, str) and value in self.operators:
            result.append(value)
        return result

    def create_link(self, source_op, target_op, source_port="output-0", target_port="input-0"):
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

    def resolve_func_name(self, node):
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id, node.id)
        elif isinstance(node, ast.Attribute):
            value = self.resolve_func_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        return None

    def _add_alias(self, alias, original):
        if self.current_scope[-1] == "global":
            self.aliases[alias] = original



if __name__ == '__main__':
    test_code = textwrap.dedent("""
        import pandas as pd

        a = 123
        b = "string"

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
        print(f"{var} -> {val.name} {val.value} {val.type}")

    print("\n生成的 Operators：")
    for op_id, op in analyzer.operators.items():
        print(op)

    print("\n生成的 Links：")
    for link_id, link in analyzer.links.items():
        print(link)