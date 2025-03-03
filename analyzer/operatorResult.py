class OperatorResult:
    """
    用于存储 operator 调用的返回结果，
    包含 operatorID 和返回类型（op_type），
    方便后续扩展。
    """
    def __init__(self, op_id, op_type, op_content):
        self.op_id = op_id
        self.op_type = op_type
        self.op_content = op_content

    def to_dict(self):
        # 返回存储 operator 的详细内容可以直接取 self.operatorID 对应的 operator 字典
        # 如果需要单独展示返回类型，也可以添加 op_type 信息。
        return {
            "op_id": self.op_id,
            "op_type": self.op_type,
            "op_content": self.op_content
        }