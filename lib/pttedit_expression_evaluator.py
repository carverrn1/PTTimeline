import re
import traceback

from ptt_debugging import Debugging

debugging = None  # Set by pttedit.py after import: ptt_expression_evaluator.debugging = debugging


def exception_traceback(e: Exception) -> str:
    return '\n'.join([
        ''.join(traceback.format_exception_only(None, e)).strip(),
        ''.join(traceback.format_exception(None, e, e.__traceback__)).strip()
    ])


GENERIC_RESULT_ERROR = 'ERR'
EXPRESSION_RESULT_ERROR = 'EXPR_ERR'
START_TIME_RESULT_ERROR = 'STRT_ERR'
ENDTIME_RESULT_ERROR = 'END_ERR'
DURATION_RESULT_ERROR = 'DRTN_ERR'
CIRCULAR_REFERENCE_RESULT_ERROR = 'CIRC_ERR'


class ResultError(Exception):
    def __init__(self, errorCode=GENERIC_RESULT_ERROR, errorMessage=None, errorLocation=None):
        self.errorCode = errorCode              # error code and exception str() value
        self.errorMessage = errorMessage        # detailed error message
        self.errorLocation = errorLocation      # reference to location (i.e. ProcessName:TaskName:ColumnName) that contains the error
        super().__init__(errorCode)

class ExpressionResultError(ResultError):
    def __init__(self, errorMessage=None, errorLocation=None):
        super().__init__(EXPRESSION_RESULT_ERROR, errorMessage=errorMessage, errorLocation=errorLocation)

class StartTimeResultError(ResultError):
    def __init__(self, errorMessage=None, errorLocation=None):
        super().__init__(START_TIME_RESULT_ERROR, errorMessage=errorMessage, errorLocation=errorLocation)

class EndTimeResultError(ResultError):
    def __init__(self, errorMessage=None, errorLocation=None):
        super().__init__(ENDTIME_RESULT_ERROR, errorMessage=errorMessage, errorLocation=errorLocation)

class DurationResultError(ResultError):
    def __init__(self, errorMessage=None, errorLocation=None):
        super().__init__(DURATION_RESULT_ERROR, errorMessage=errorMessage, errorLocation=errorLocation)

class CircularReferenceResultError(ResultError):
    def __init__(self, errorMessage=None, errorLocation=None):
        super().__init__(CIRCULAR_REFERENCE_RESULT_ERROR, errorMessage=errorMessage, errorLocation=errorLocation)


def get_object_methods(object):
    method_names = []
    for method_name in dir(object):
        try:
            if callable(getattr(object, method_name)):
                method_names.append(str(method_name))
            #end if
        except Exception:
            method_names.append(str(method_name))
        #end try
    #end for method_name
    return method_names
#end def get_object_methods


def calculation_error_value(err_no=None):
    if (err_no):
        calculation_error_value_txt = f'ERR:{err_no}'
    else:
        calculation_error_value_txt = f'ERR:'
    return(calculation_error_value_txt)


class BadFormulaError(ValueError):
  def __init__(self, message):
    self.message = message

class CircularReferenceError(ValueError):
  def __init__(self, message):
    self.message = message


def _split_top_level_args(args_str):
    """Split a comma-separated argument string respecting nested parentheses.

    Example:
        "End(p1:t1), End(p2:t1), End(p3:t2)"
        -> ["End(p1:t1)", "End(p2:t1)", "End(p3:t2)"]

    A plain str.split(',') would break on commas inside nested function calls.
    This walks the string tracking parenthesis depth and only splits at depth 0.
    """
    args = []
    depth = 0
    current = []
    for ch in args_str:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        args.append(''.join(current).strip())
    return args


class ExpressionEvaluator:
    def __init__(self):
        # Dictionary to store single-argument function mappings (Start, End, Duration, etc.)
        # Registered functions receive: (process_task: str, dependencies: list, referenceLocation: str)
        debugging.enter()
        self.function_mapping = {}
        # Dictionary to store multi-argument function mappings (Min, Max, etc.)
        # Registered functions receive: (values: list[float], dependencies: list, referenceLocation: str)
        self.multiarg_function_mapping = {}
        debugging.leave()

    def register_function(self, function_name, function):
        # Register a single-argument function with the evaluator
        debugging.enter(f'function_name={function_name}')
        self.function_mapping[function_name] = function
        debugging.leave()

    def register_multiarg_function(self, function_name, function):
        # Register a multi-argument function with the evaluator
        debugging.enter(f'function_name={function_name}')
        self.multiarg_function_mapping[function_name] = function
        debugging.leave()

    def evaluate_token(self, token, dependencies, referenceLocation, callerProcessTask):
        debugging.enter(f'token={token}, dependencies={dependencies}, referenceLocation={referenceLocation}, callerProcessTask={callerProcessTask}')
        result = ExpressionResultError(errorMessage=f'Invalid Token: {token}', errorLocation=referenceLocation)
        # Try to parse the token as a float
        try:
            result = float(token)
        except ValueError as e:
            debugging.print(f'float() Exception: {e}')
            # If not a number, it must be a function call
            match = re.match(r'(\w+)\((.*)\)$', token, re.DOTALL)
            if match:
                function_name = match.group(1)
                args_str = match.group(2)
                args = _split_top_level_args(args_str)
                debugging.print(f'Token is a function call: {function_name} with args: {args}')
                # Multi-argument function path (Min, Max, etc.)
                if function_name in self.multiarg_function_mapping:
                    evaluated_args = []
                    for arg in args:
                        # Each branch gets its own snapshot of the call stack so that
                        # nodes visited in one branch do not pollute sibling branches.
                        branch_dependencies = dependencies[:]
                        arg_result = self.evaluate_expression(arg, branch_dependencies, referenceLocation, callerProcessTask)
                        if isinstance(arg_result, type(ResultError())):
                            debugging.leave(f'ERROR: multi-arg evaluation failed for arg={arg}')
                            return arg_result
                        evaluated_args.append(arg_result)
                    debugging.print(f'Calling multi-arg function "{function_name}" with evaluated_args={evaluated_args}')
                    try:
                        result = self.multiarg_function_mapping[function_name](evaluated_args, dependencies, referenceLocation)
                    except Exception as e:
                        result = ExpressionResultError(errorMessage=f'Function: {function_name}({args_str}) Exception: {e}', errorLocation=referenceLocation)
                        debugging.leave(f'ERROR: result.errorMessage={result.errorMessage}')
                        return(result)
                # Single-argument function path (Start, End, Duration, etc.)
                elif function_name in self.function_mapping:
                    parameter = args[0] if args else args_str
                    debugging.print(f'Token is a single-arg function call: {function_name} with parameter: {parameter}')
                    expanded_parameter = parameter
                    if ('$' in parameter):
                        try:
                            process_name, task_name = parameter.split(':')
                            caller_process_name, caller_task_name = callerProcessTask.split(':')
                            if (process_name == '$'): process_name = caller_process_name
                            if (task_name == '$'): task_name = caller_task_name
                            expanded_parameter = f"{process_name}:{task_name}"
                        except Exception as e:
                            pass
                        debugging.print(f"Macro Expansion: parameter={parameter}, expanded_parameter={expanded_parameter}")
                    this_dependency = f'{expanded_parameter}.{function_name}'
                    debugging.print(f"this_dependency={this_dependency}, referenceLocation={referenceLocation}")
                    if (this_dependency in dependencies):
                        result = CircularReferenceResultError(errorMessage=f"Circular Reference: {this_dependency}", errorLocation=referenceLocation)
                        debugging.leave(f'ERROR: result.errorMessage={result.errorMessage}')
                        return(result)
                    dependencies.append(this_dependency)
                    # Call the registered function with the expanded_parameter
                    debugging.print(f'Call the registered function "{function_name}" with the parameter "{expanded_parameter}" and dependencies "{dependencies}"')
                    try:
                        result = self.function_mapping[function_name](expanded_parameter, dependencies, referenceLocation)
                    except Exception as e:
                        result = ExpressionResultError(errorMessage=f'Function: {function_name}({expanded_parameter}) Exception: {e}', errorLocation=referenceLocation)
                        debugging.leave(f'ERROR: result.errorMessage={result.errorMessage}')
                        return(result)
                    finally:
                        # Pop this_dependency from the call stack so sibling branches
                        # can legitimately reference the same node (diamond dependency
                        # pattern) without triggering a false circular reference error.
                        dependencies.remove(this_dependency)
                else:
                    result = ExpressionResultError(errorMessage=f'Function not defined: "{function_name}"', errorLocation=referenceLocation)
        if (isinstance(result, type(ResultError()))):
            debugging.leave(f'ERROR: result.errorMessage={result.errorMessage}')
        else:
            debugging.leave(f'token={token}, result={result}')
        return(result)

    def infix_to_rpn(self, tokens):
        debugging.enter()
        precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
        output = []
        stack = []

        for token in tokens:
            if token in {'+', '-', '*', '/'}:
                while stack and precedence.get(stack[-1], 0) >= precedence.get(token, 0):
                    output.append(stack.pop())
                stack.append(token)
            else:
                output.append(token)

        while stack:
            output.append(stack.pop())

        debugging.leave()
        return output

    def tokenize_expression(self, expression):
        debugging.enter(f'expression={expression}')
        # Tokenize the expression using a character-by-character scanner so that
        # function calls with nested parentheses (e.g. Max(End(p:t), End(p:t)))
        # are captured as a single token regardless of nesting depth.
        tokens = []
        i = 0
        n = len(expression)
        while i < n:
            ch = expression[i]
            # Skip whitespace
            if ch.isspace():
                i += 1
                continue
            # Arithmetic operators
            if ch in '+-*/':
                tokens.append(ch)
                i += 1
                continue
            # Word: identifier, number, or start of a function call
            m = re.match(r'[\w.]+', expression[i:])
            if m:
                word = m.group(0)
                j = i + len(word)
                if j < n and expression[j] == '(':
                    # Function call — scan forward to the matching closing paren
                    depth = 0
                    k = j
                    while k < n:
                        if expression[k] == '(':
                            depth += 1
                        elif expression[k] == ')':
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    tokens.append(expression[i:k+1])
                    i = k + 1
                else:
                    # Plain number or bare identifier
                    tokens.append(word)
                    i = j
            else:
                i += 1  # skip unrecognised character
        debugging.leave(f'tokens={tokens}')
        return(tokens)

    def is_token_a_formula(self, token):
        debugging.enter(f'token={token}')
        is_formula = False
        function_name = None
        parameter = None
        # Match any function call: word followed by balanced parentheses content
        match = re.match(r'(\w+)\((.*)\)$', token, re.DOTALL)
        if (match):
            function_name = match.group(1)
            parameter = match.group(2)
            is_formula = True
        debugging.leave(f'is_formula={is_formula}, token={token}, function_name={function_name}, parameter={parameter}, ')
        return(is_formula, function_name, parameter)

    def get_expression_dependencies(self, expression, callerProcessTask):
        """Extract Process:Task dependencies from a formula expression.

        Returns a set of 'Process:Task' strings that this expression references.
        Handles $ macro expansion using callerProcessTask.
        """
        debugging.enter(f'expression={expression}, callerProcessTask={callerProcessTask}')
        expression_dependencies = set()

        if not expression:
            debugging.leave(f'expression_dependencies={expression_dependencies} (empty expression)')
            return expression_dependencies

        # Short-circuit: if expression is a plain number, no dependencies
        try:
            float(expression)
            debugging.leave(f'expression_dependencies={expression_dependencies} (plain number)')
            return expression_dependencies
        except (ValueError, TypeError):
            pass

        # Tokenize and check each token for function calls
        tokens = self.tokenize_expression(expression)
        for token in tokens:
            is_token_formula, function_name, parameter = self.is_token_a_formula(token)
            if not is_token_formula:
                continue
            if function_name in self.multiarg_function_mapping:
                # Multi-arg function (Min, Max, etc.) — recurse into each argument
                args = _split_top_level_args(parameter)
                for arg in args:
                    nested_deps = self.get_expression_dependencies(arg, callerProcessTask)
                    expression_dependencies.update(nested_deps)
            elif function_name in self.function_mapping:
                # Single-arg function (Start, End, Duration, etc.) — expand $ macros
                expanded_parameter = parameter
                if '$' in parameter:
                    try:
                        process_name, task_name = parameter.split(':')
                        caller_process_name, caller_task_name = callerProcessTask.split(':')
                        if process_name == '$':
                            process_name = caller_process_name
                        if task_name == '$':
                            task_name = caller_task_name
                        expanded_parameter = f"{process_name}:{task_name}"
                    except Exception:
                        pass
                expression_dependencies.add(expanded_parameter)

        debugging.leave(f'expression_dependencies={expression_dependencies}')
        return expression_dependencies

    def evaluate_expression(self, expression=None, dependencies=[], referenceLocation=None, callerProcessTask=None):
        debugging.enter(f'expression={expression}, dependencies={dependencies}, referenceLocation={referenceLocation}, callerProcessTask={callerProcessTask}')
        # Pre-process: replace bare '(' (not preceded by a word char) with '_grp('
        # so that parenthesized grouping like (3-2)*2 is handled as _grp(3-2)*2
        expression = re.sub(r'(?<!\w)\(', '_grp(', expression)
        debugging.print(f'expression after _grp substitution={expression}')
        tokens = self.tokenize_expression(expression)
        debugging.print(f'tokens={tokens}')

        # Convert infix expression to RPN
        rpn_tokens = self.infix_to_rpn(tokens)
        debugging.print(f'rpn_tokens={rpn_tokens}')

        # Evaluate expression from RPN
        stack = []
        for token in rpn_tokens:
            result = None
            debugging.print(f'token={token}')
            # Evaluate each token and perform math operations
            if token in {'+', '-', '*', '/'}:
                debugging.print(f'Token IS Operator: {token}')
                # Ensure both operands are available
                operand2 = stack.pop()
                if len(stack) < 1:
                    operand1 = 0
                else:
                    operand1 = stack.pop()
                debugging.print(f'Operand1: {operand1}')
                debugging.print(f'Operand2: {operand2}')
                try:
                    if token == '+':
                        result = operand1 + operand2
                    elif token == '-':
                        result = operand1 - operand2
                    elif token == '*':
                        result = operand1 * operand2
                    elif token == '/':
                        if operand2 == 0:
                            debugging.leave(f'Exception: Division by zero.')
                            raise ValueError(f'Division by zero.')
                        result = operand1 / operand2
                except Exception as e:
                    result = ExpressionResultError()
                debugging.print(f'Performing operation: {operand1} {token} {operand2}')
                stack.append(result)
                debugging.print(f'Stack: {stack}')
            else:
                debugging.print(f'Token is Operand: {token}')
                try:
                    result = self.evaluate_token(token, dependencies, referenceLocation, callerProcessTask)
                    stack.append(result)
                except Exception as e:
                    debugging.leave(f'evaluate_token() Exception: {e}')
                    raise
                debugging.print(f'Stack after evaluating token: {stack}')
            debugging.print(f'result={result}, type(result)={type(result)}')
            # If any part of any expression evaluate returns a ResultError type as the value then immediately return the error
            if (isinstance(result, type(ResultError()))):
                debugging.leave(f'result={result}')
                return(result)
        if len(stack) != 1:
            debugging.leave(f'Exception: Invalid expression. (len(stack) != 1)')
            result = ExpressionResultError(errorMessage=f'Invalid Expression: {expression}', errorLocation=referenceLocation)
            return(result)
        result = round(stack[0], 3)
        debugging.leave(f'result={result}')
        return(stack[0])
