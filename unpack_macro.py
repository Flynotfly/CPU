from errors import MESSAGES

CALLER_SAVED = ['r0', 'r1', 'r2']
CALLEE_SAVED = ['r3', 'r4', 'r5']

global_function = {
    'is_inside': False,
    'args_quantity': 0,
    'saved_registers': [],
}


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
            if global_function['is_active']:
                raise ValueError()

            if len(parts) == 1:
                raise ValueError()

            global_function['is_active'] = True
            global_function['args_quantity'] = 0
            global_function['saved_registers'] = []

            code = [
                f"label {parts[1]}",
                "push bp",
                "mov sp bp",
            ]

            mode = None
            for tok in parts[2:]:
                if tok in ("save", "args"):
                    mode = tok
                elif mode == "save":
                    if tok in CALLEE_SAVED:
                        global_function['saved_registers'].append(tok)
                        code.append(f'push {tok}')
                    else:
                        raise ValueError()
                elif mode == "args":
                    if global_function['args_quantity'] is None:
                        global_function['args_quantity'] = int(tok)
                    else:
                        raise ValueError()
                else:
                    raise ValueError()

            if global_function['args_quantity']:
                code.append(f"sub sp {global_function['args_quantity']} sp")
            return code_to_str(code)

        case "ret":
            ...
        case "call":
            ...
        case "if":
            ...
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
                print(f"Exception on line {ln}: {e}")
            else:
                fout.write(out_line + "\n")

