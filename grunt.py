import re

class Grunt:
    def __init__(self):
        # Initialize variables, handlers, and macros
        self.variables = {}
        self.macros = {}
        self.operators = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
            '*': lambda a, b: a * b,
            '/': lambda a, b: a / b,  # Be mindful of division by zero
            '<': lambda a, b: a < b,
            '>': lambda a, b: a > b,
            '<=': lambda a, b: a <= b,
            '>=': lambda a, b: a >= b,
            '==': lambda a, b: a == b,
            '!=': lambda a, b: a != b,
        }
        self.gcode_handlers = {}
        self.program = ""

    def is_float(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def register(self, code, handler):
        self.gcode_handlers[code] = handler

    def replace_gcode_vars(self, expr):
        expr = re.sub(r'#(\d+)', r'var_\1', expr)
        expr = re.sub(r'#([a-zA-Z_]\w*)', r'var_\1', expr)
        expr = expr.replace("LT", "<").replace("GT", ">").replace("LE", "<=").replace("GE", ">=").replace("EQ", "==").replace("NE", "!=")
        return expr

    def parse_expression(self, expr):
        expr = self.replace_gcode_vars(expr)

        def tokenize(expression):
            tokens = re.findall(r'\d+\.?\d*|[+\-*/<>=!()]+|[A-Za-z_]\w*', expression)
            return tokens

        tokens = tokenize(expr)

        if tokens[0] == "READ":
            if self.gcode_handlers["READ"]:
                value = self.gcode_handlers["READ"](int(self.parse_expression(tokens[1])))  # Replace with your actual function to read from a pin
            else:
                value = 0
            return value
        elif tokens[0] == "RECV":
            if self.gcode_handlers["RECV"]:
                message = self.gcode_handlers["RECV"](float(self.parse_expression(tokens[1])))  # Replace with your actual function to receive a message
            else:
                message = ""
            return message

        def to_rpn(tokens):
            precedence = {'+': 1, '-': 1, '*': 2, '/': 2, '<': 0, '>': 0, '<=': 0, '>=': 0, '==': 0, '!=': 0}
            output = []
            ops_stack = []

            for token in tokens:
                if re.match(r'^\d+\.?\d*$', token) or re.match(r'^[A-Za-z_]\w*$', token):  # Operand
                    output.append(token)
                elif token in self.operators:  # Operator
                    while ops_stack and precedence.get(ops_stack[-1], 0) >= precedence[token]:
                        output.append(ops_stack.pop())
                    ops_stack.append(token)
                elif token == '(':
                    ops_stack.append(token)
                elif token == ')':
                    while ops_stack and ops_stack[-1] != '(':
                        output.append(ops_stack.pop())
                    ops_stack.pop()  # Remove '(' from stack

            while ops_stack:
                output.append(ops_stack.pop())

            return output

        def evaluate_rpn(rpn):
            stack = []

            for token in rpn:
                if self.is_float(token):  # Numeric value
                    stack.append(float(token))
                elif token in self.variables:  # Variable
                    stack.append(self.variables[token])
                elif token in self.operators:  # Operator
                    if len(stack) < 2:
                        raise ValueError(f"Error: Not enough operands in stack for operation '{token}'")
                    b = stack.pop()
                    a = stack.pop()
                    result = self.operators[token](a, b)
                    stack.append(result)
                else:
                    raise ValueError(f"Unexpected token in expression: {token}")

            if len(stack) != 1:
                raise ValueError(f"Error in expression evaluation, stack: {stack}")

            return stack[0]

        rpn = to_rpn(tokens)
        return evaluate_rpn(rpn)

    def evaluate_arguments(self, arguments):
        evaluated_args = {}
        for arg in arguments:
            if '[' in arg and ']' in arg:
                key = arg[0]
                expression = arg[arg.find('[') + 1:arg.find(']')]
                evaluated_value = self.parse_expression(expression)
                evaluated_args[key] = evaluated_value
            else:
                key = arg[0]
                value = arg[1:]
                try:
                    evaluated_args[key] = float(value)
                except ValueError:
                    evaluated_args[key] = value
        return evaluated_args

    def execute_gcode(self, command):
        code, *args = command.split()
        evaluated_args = self.evaluate_arguments(args)
        if code in self.gcode_handlers:
            self.gcode_handlers[code](evaluated_args)
        else:
            print(f"Unknown command: {command}")

    def execute_command(self, command):
        if "=" in command:
            var_name, expr = map(str.strip, command.split("=", 1))
            var_name = var_name[var_name.find("#"):]
            if var_name.startswith("#"):
                var_name = self.replace_gcode_vars(var_name)
                value = self.parse_expression(expr)
                self.variables[var_name] = value

        elif command.startswith("G") or command.startswith("M"):
            self.execute_gcode(command)

        elif command.startswith("WRITE"):
            args = command.split()
            if args[1].isdigit() or ('[' in args[1] and len(args) == 3):  # Writing to a pin (including with variables)
                pin_number = self.parse_expression(args[1]) if '[' in args[1] else args[1]
                value = self.parse_expression(args[2]) if '[' in args[2] else float(args[2])
                if self.gcode_handlers["WRITEPIN"]:
                    self.gcode_handlers["WRITEPIN"](pin_number, value)
            else:  # Sending a message
                message = " ".join(args[1:])
                e = re.findall(r'\[.*?\]', message)
                if len(e) > 0:
                    for a in e:
                        b = self.parse_expression(a[1:-1])
                        message = message.replace(a, str(b))
                if self.gcode_handlers["WRITEMSG"]:
                    self.gcode_handlers["WRITEMSG"](message)

    def execute_macro(self, macro_name, args):
        if macro_name not in self.macros:
            raise ValueError(f"Macro {macro_name} not found")
        macro_body = self.macros[macro_name]
        for i, arg in enumerate(args):
            macro_body = re.sub(r'\$' + str(i + 1), str(arg), macro_body)
        evaluated_body = []
        for line in macro_body.splitlines():
            evaluated_line = re.sub(r'\[(.+?)\]', lambda m: str(self.parse_expression(m.group(1))), line)
            evaluated_body.append(evaluated_line)
        self.parse_gcode(evaluated_body)

    def parse_gcode(self, lines):
        i = 0
        while i < len(lines):
            line = lines[i].split(';')[0].strip()
            if not line:
                i += 1
                continue

            commands = line.split()
            if len(commands) == 0:
                i += 1
                continue

            if commands[0] == "MACRO":
                if i + 1 < len(lines):
                    macro_name = commands[1]
                    macro_body = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith("ENDMACRO"):
                        macro_body.append(lines[i])
                        i += 1
                    self.macros[macro_name] = "\n".join(macro_body)
                else:
                    raise ValueError(f"MACRO command at line {i+1} is incomplete")
                i += 1

            elif commands[0].startswith("IF"):
                condition = line[2:].strip()
                if not condition:
                    raise ValueError(f"IF condition is empty at line {i+1}: {line}")
                if self.parse_expression(condition):
                    i += 1
                    continue
                while i < len(lines) and not lines[i].startswith("ELSEIF") and not lines[i].startswith("ELSE") and not lines[i].startswith("ENDIF"):
                    i += 1
                if lines[i].startswith("ELSEIF"):
                    condition = lines[i][6:].strip()
                    if not condition:
                        raise ValueError(f"ELSEIF condition is empty at line {i+1}: {line}")
                    if self.parse_expression(condition):
                        i += 1
                        continue

            elif commands[0].startswith("FOR"):
                var, start, end = commands[1], commands[2], commands[3]
                start = self.parse_expression(start)
                end = self.parse_expression(end)
                loop_body = []
                i += 1
                while i < len(lines) and not lines[i].startswith("ENDFOR"):
                    loop_body.append(lines[i])
                    i += 1
                for val in range(int(start), int(end) + 1):
                    self.variables[self.replace_gcode_vars(var)] = val
                    self.parse_gcode(loop_body)

            elif commands[0].startswith("WHILE"):
                condition = re.match(r'WHILE \[(.+)\]', line).group(1)
                if not condition:
                    raise ValueError(f"WHILE condition is empty at line {i+1}: {line}")
                loop_body = []
                i += 1
                while i < len(lines) and not lines[i].startswith("ENDWHILE"):
                    loop_body.append(lines[i])
                    i += 1
                while self.parse_expression(condition):
                    self.parse_gcode(loop_body)

            elif commands[0].startswith("CALL"):
                _, macro_name, *args = commands
                argsJoin = " ".join(args)
                e = re.findall(r'\[.*?\]', argsJoin)
                if len(e) > 0:
                    for a in e:
                        b = self.parse_expression(a)
                        argsJoin = argsJoin.replace(a, str(int(b)))
                args = argsJoin.split(" ")
                self.execute_macro(macro_name, args)

            else:
                self.execute_command(line)

            i += 1

    def run(self, program):
        self.parse_gcode(program.split("\n"))




