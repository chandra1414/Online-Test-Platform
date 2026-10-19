import ast
import os
import shutil
import subprocess
import sys
import tempfile
import time


BLOCKED_MODULES = {
    'os', 'subprocess', 'shutil', 'socket', 'urllib', 'requests',
    'ctypes', 'threading', 'multiprocessing', 'signal', 'asyncio', 'pty',
    'posix', 'resource', 'pathlib', 'pip', 'importlib', 'inspect', 'code',
    'webbrowser', 'ftplib', 'smtplib', 'http', 'xmlrpc', 'socketserver',
    'winreg', 'msvcrt', '_winapi'
}

BLOCKED_NAMES = {
    '__import__', 'eval', 'exec', 'open', 'compile', 'globals', 'locals',
    'breakpoint', 'input_raw', '__loader__', '__spec__'
}


class SecurityViolation(Exception):
    pass


class CodeSecurityValidator(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in BLOCKED_MODULES:
                self.violations.append(f"Security Warning: Direct import of '{alias.name}' is strictly prohibited.")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in BLOCKED_MODULES:
                self.violations.append(f"Security Warning: Importing from '{node.module}' is strictly prohibited.")
        self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in BLOCKED_NAMES:
            self.violations.append(f"Security Warning: Built-in function or identifier '{node.id}' is blocked for security.")
        self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in {'__subclasses__', '__bases__', '__mro__', '__globals__', '__code__'}:
            self.violations.append(f"Security Warning: Access to introspective attribute '{node.attr}' is restricted.")
        self.generic_visit(node)


def validate_python_code(code_str: str):
    """
    Statically analyzes code to ensure safety prior to process execution.
    Returns (is_safe: bool, message: str)
    """
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} on line {e.lineno}"
    except Exception as e:
        return False, f"Invalid code format: {str(e)}"

    validator = CodeSecurityValidator()
    validator.visit(tree)
    if validator.violations:
        return False, "\n".join(validator.violations)

    return True, "Code passed security verification."


def execute_sandboxed_code(code_str: str, input_data: str = "", time_limit: float = 2.0) -> dict:
    """
    Executes Python code in an isolated subprocess with bounded execution time and strict environment.
    Never runs code directly in Django's process.
    """
    # 1. AST Validation
    is_safe, sec_msg = validate_python_code(code_str)
    if not is_safe:
        return {
            'status': 'SECURITY_VIOLATION',
            'output': '',
            'error': sec_msg,
            'execution_time': 0.0,
            'passed': False
        }

    # 2. Setup isolated temporary directory
    temp_dir = tempfile.mkdtemp(prefix="agy_sandbox_")
    script_path = os.path.join(temp_dir, "solution.py")

    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(code_str)

        # Build clean environment with only Python executable path
        py_exe = sys.executable
        # Flags:
        # -I : Run in isolated mode (ignore environment variables, no cwd in sys.path)
        # -B : Don't write .pyc bytecode files
        cmd = [py_exe, "-I", "-B", script_path]

        # Minimal safe environment
        clean_env = {
            'SYSTEMROOT': os.environ.get('SYSTEMROOT', r'C:\Windows'),
            'PATH': os.path.dirname(py_exe),
            'PYTHONIOENCODING': 'utf-8',
        }

        start_time = time.time()
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=temp_dir,
            env=clean_env
        )

        try:
            stdout_data, stderr_data = process.communicate(input=input_data, timeout=time_limit)
            exec_time = round(time.time() - start_time, 3)

            # Limit output length to prevent payload bombs (max 32KB)
            if len(stdout_data) > 32768:
                stdout_data = stdout_data[:32768] + "\n...[Output truncated - exceeded 32KB]"

            if process.returncode != 0:
                return {
                    'status': 'RUNTIME_ERROR',
                    'output': stdout_data,
                    'error': stderr_data.strip() or f"Process exited with code {process.returncode}",
                    'execution_time': exec_time,
                    'passed': False
                }

            return {
                'status': 'SUCCESS',
                'output': stdout_data,
                'error': '',
                'execution_time': exec_time,
                'passed': True
            }

        except subprocess.TimeoutExpired:
            process.kill()
            try:
                process.communicate(timeout=0.5)
            except Exception:
                pass
            return {
                'status': 'TIME_LIMIT_EXCEEDED',
                'output': '',
                'error': f"Time Limit Exceeded: Execution took longer than {time_limit} seconds.",
                'execution_time': time_limit,
                'passed': False
            }

    finally:
        # Securely destroy temporary scratch folder and script
        shutil.rmtree(temp_dir, ignore_errors=True)


def evaluate_coding_question(code_str: str, test_cases, time_limit: float = 2.0) -> dict:
    """
    Evaluates submitted code against an iterable of TestCase objects.
    Returns summary result dictionary.
    """
    total_cases = len(test_cases)
    if total_cases == 0:
        return {
            'passed_all': True,
            'cases_passed': 0,
            'total_cases': 0,
            'percentage': 100.0,
            'details': [],
            'error_summary': ''
        }

    cases_passed = 0
    details = []
    error_summary = ''

    for idx, tc in enumerate(test_cases, start=1):
        res = execute_sandboxed_code(code_str, input_data=tc.input_data, time_limit=time_limit)
        
        tc_passed = False
        message = ''

        if res['status'] == 'SUCCESS':
            # Compare output with expected output (normalizing line endings and strip whitespace)
            student_out = res['output'].replace('\r\n', '\n').strip()
            expected_out = tc.expected_output.replace('\r\n', '\n').strip()

            if student_out == expected_out:
                tc_passed = True
                cases_passed += 1
                message = "Passed"
            else:
                message = "Wrong Answer (Output Mismatch)"
        elif res['status'] == 'SECURITY_VIOLATION':
            message = res['error']
            error_summary = res['error']
        elif res['status'] == 'TIME_LIMIT_EXCEEDED':
            message = "Time Limit Exceeded"
            if not error_summary:
                error_summary = message
        else:
            message = f"Runtime Error: {res['error']}"
            if not error_summary:
                error_summary = res['error']

        details.append({
            'case_num': idx,
            'is_sample': tc.is_sample,
            'passed': tc_passed,
            'status': res['status'],
            'message': message,
            'execution_time': res['execution_time'],
            # Only reveal actual vs expected output for sample test cases (not hidden ones)
            'sample_input': tc.input_data if tc.is_sample else '(Hidden Test Case)',
            'expected_output': tc.expected_output if tc.is_sample else '(Hidden)',
            'actual_output': res['output'] if tc.is_sample else ('(Hidden output)' if not tc_passed else 'Passed')
        })

    pct = round((cases_passed / total_cases) * 100, 1)
    return {
        'passed_all': (cases_passed == total_cases),
        'cases_passed': cases_passed,
        'total_cases': total_cases,
        'percentage': pct,
        'details': details,
        'error_summary': error_summary
    }
