class VariableInfo:
    def __init__(self, name, value, var_type=None):
        self.name = name
        self.value = value
        if var_type is not None:
            self.type = var_type
        else:
            self.type = self.get_variable_type(value)

    def get_variable_type(self, value):
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
            'name': self.name,
            'value': self.value,
            'type': self.type
        }