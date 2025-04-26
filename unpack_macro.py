from queue import LifoQueue

from errors import MESSAGES
from utils import is_condition


CALLER_SAVED = ['r0', 'r1', 'r2']
CALLEE_SAVED = ['r3', 'r4', 'r5']

global_function = {
    'is_inside': False,
    'args_quantity': 0,
    'saved_registers': [],
}

nests = LifoQueue()
free_sys_label = 0


def get_free_sys_label():
    global free_sys_label
    result = "_" + str(free_sys_label)
    free_sys_label += 1
    return result


def code_to_str(code: list) -> str:
    result = ""
    for line in code:
        result = result + line + "\n"
    return result


def process_line(line: str) -> str:
    parts = line.split()
    op = parts[0]

    match op:
        case "def":
            if global_function['is_inside']:
                raise ValueError()

            if not nests.empty():
                raise ValueError()

            if len(parts) == 1:
                raise ValueError()

            global_function['is_inside'] = True

            code = [
                f"label {parts[1]}",
                "push bp",
                "mov sp bp",
            ]

            mode = None
            for tok in parts[2:]:
                if tok in ("save", "reserve"):
                    mode = tok
                elif mode == "save":
                    if tok in CALLEE_SAVED:
                        global_function['saved_registers'].append(tok)
                        code.append(f'push {tok}')
                    else:
                        raise ValueError()
                elif mode == "reserve":
                    if not global_function['args_quantity']:
                        global_function['args_quantity'] = int(tok)
                    else:
                        raise ValueError()
                else:
                    raise ValueError()

            if global_function['args_quantity']:
                code.append(f"sub sp {global_function['args_quantity']} sp")
            return code_to_str(code)

        case "ret":
            if not global_function['is_inside']:
                raise ValueError()

            if not nests.empty():
                raise ValueError()

            if not len(parts) == 2:
                raise ValueError()

            code = [f"mov {parts[1]} rv"]
            if global_function['args_quantity']:
                code.append(f"add sp {global_function['args_quantity']} sp")
            for register in global_function['saved_registers']:
                code.append(f"pop {register}")
            code.append("pop bp")
            code.append("pop pc")

            global_function['is_inside'] = False
            global_function['args_quantity'] = 0
            global_function['saved_registers'] = []

            return code_to_str(code)

        case "call":
            if len(parts) == 1:
                raise ValueError()

            code = []
            goto_dst = parts[1]
            saved_registers = []
            args = []
            mode = None
            for tok in parts[2:]:
                if tok in ("save", "args"):
                    mode = tok
                elif mode == "save":
                    if tok in CALLER_SAVED:
                        saved_registers.append(tok)
                        code.append(f'push {tok}')
                    else:
                        raise ValueError()
                elif mode == "args":
                    args.append(tok)
                else:
                    raise ValueError()

            for arg in reversed(args):
                code.append(f'push {arg}')
            code.append("push pc+")
            code.append(f"jmp {goto_dst}")
            if args:
                code.append(f"add sp {len(args)} sp")
            for register in saved_registers:
                code.append(f"pop {register}")
            return code_to_str(code)

        case "if":
            if not len(parts) == 4:
                raise ValueError()

            if not is_condition(*parts[1:]):
                raise ValueError()

            sys_label = get_free_sys_label()
            true_label = sys_label + "T"
            false_label = sys_label + "F"
            nests.put({
                'condition': 'if',
                'label': sys_label,
                'elif': 0,
            })
            command, arg1, arg2 = parts[1:]
            code = [
                f"{command} {arg1} {arg2} {true_label}",
                f"jmp {false_label}",
                f"sys_label {true_label}",
            ]
            return code_to_str(code)

        case "elif":
            ...
        case "else":
            ...
        case "for":
            ...
        case "while":
            ...
        case "end":
            ...
        case _:
            return line


def unpack_macro_commands(in_path: str, out_path: str):
    with open(in_path, 'r', encoding='utf-8') as fin, \
            open(out_path, 'w', encoding='utf-8') as fout:
        for ln, line in enumerate(fin, 1):
            try:
                out_line = process_line(line)
            except ValueError as e:
                raise ValueError
                print(f"Exception on line {ln}: {e}")
            else:
                fout.write(out_line)

