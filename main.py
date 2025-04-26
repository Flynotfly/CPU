import re

from clean import clean_code
from unpack_macro import unpack_macro_commands

INPUT_FILE = 'C:/Users/1/Documents/TuringComplete/input.txt'
CLEAN_FILE = 'C:/Users/1/Documents/TuringComplete/clean.txt'
RESOLVED_MACRO_FILE = 'C:/Users/1/Documents/TuringComplete/resovled_macro.txt'
LABELS_FILE = 'C:/Users/1/Documents/TuringComplete/with_labels.txt'
OUTPUT_FILE = 'C:/Users/1/Documents/TuringComplete/output.txt'


def to_u16(x: int) -> int:
    return x & 0xFFFF


EMPTY = to_u16(-1)

# Битовые позиции
IM1_BIT = 15
IM2_BIT = 14
OPCODE_SHIFT = 9
SUBTYPE_SHIFT = 6
SUBFUNC_SHIFT = 2

# IM1 IM2 Reserve OP  Type Func  Reserve
# 0   0   0       0000 000  0000 00

# OPCODE
OPCODES = {
    'nop': 0b0000,
    'calc': 0b0001,
    'cond': 0b0010,
    'copy': 0b0011,
}

TYPES = {
    'nop': {
        'nop': 0b000,
        'exit': 0b001,
    },
    'calc': {
        'base': 0b000,
        'math': 0b001,
    },
    'cond': {
        'base': 0b000,
    },
    'copy': {
        'normal': 0b000,
        'stack': 0b001,
    },
}

FUNCS = {
    'nop': {
        'nop': {
            'nop': 0b0000,
        },
        'exit': {
            'exit': 0b0000,
        },
    },
    'calc': {
        'base': {
            'not': 0b0000, 'and': 0b0001, 'or': 0b0010, 'nand': 0b0011,
            'nor': 0b0100, 'xor': 0b0101, 'xnor': 0b0110,
            'shl': 0b1000, 'shr': 0b1001, 'rol': 0b1010,
            'ror': 0b1011, 'ashr': 0b1100,
        },
        'math': {
            'neg': 0b0000, 'add': 0b0001, 'sub': 0b0010,
            'mul': 0b0011, 'div': 0b0100, 'mod': 0b0101,
        },
    },
    'cond': {
        'base': {
            'eq': 0b0000, 'lt': 0b0001, 'lte': 0b0010,
            'gt': 0b0011, 'gte': 0b0100,
            'lts': 0b1000, 'ltes': 0b1001,
            'gts': 0b1010, 'gtes': 0b1011,
        },
    },
    'copy': {
        'normal': {
            'mov': 0b0000,
        },
        'stack': {
            'push': 0b0000,
            'pop': 0b0001,
        },
    },
}

CALC_CODES_ONE_ARG = {'not', 'neg'}
CALC_CODES_TWO_ARGS = {
    'and', 'or', 'nand', 'nor', 'xor', 'xnor', 'shl', 'shr', 'ror', 'rol', 'ashr',
    'add', 'sub', 'mul', 'div', 'mod',
}
CONDITION_CODES = {'eq', 'lt', 'lte', 'gt', 'gte', 'lts', 'ltes', 'gts', 'gtes'}

REGISTERS = {
    'r0': 0,
    'r1': 1,
    'r2': 2,
    'r3': 3,
    'r4': 4,
    'r5': 5,
    'rv': 6,  # return value
    'bp': 7,  # frame pointer
    'sp': 8,  # stack pointer
    'pc': 9,  # program counter - next operation
    'pc-': 10,  # pc - 1: current operation / do not choose as dst
    'pc+': 11,  # pc + 1: next second operation / do not choose as dst
}

CALLER_SAVED = ['r0', 'r1', 'r2']
CALLEE_SAVED = ['r3', 'r4', 'r5']

labels = {}
command_line = 0
current_function = {
    'callee_saved': [],
    'reserved': 0,
    'is_active': False,
}
error_counter = 0


def increase_error_counter():
    global error_counter
    error_counter += 1


def find_opcode_path(name: str):
    """
    Search FUNCS for the given opcode name and return a tuple:
        (main_category, sub_category, opcode_name)
    Raises ValueError if not found.
    """
    for main_cat, subcats in FUNCS.items():
        for sub_cat, ops in subcats.items():
            if name in ops:
                return main_cat, sub_cat, name
    raise ValueError(f"Opcode '{name}' not found in FUNCS")


def check_length(parts: list, expect: int, op: str):
    if len(parts) != expect:
        raise ValueError(f"{op} expects {expect - 1} operands, got {len(parts) - 1}")


def parse_operand(tok: str, operand_type: str) -> tuple[int, bool] | tuple[str, bool]:
    ALLOW_NUMBER = False
    ALLOW_REGISTER = False
    ALLOW_LABELS = False

    if operand_type == 'src':
        ALLOW_NUMBER = True
        ALLOW_REGISTER = True
    elif operand_type == 'dst':
        ALLOW_REGISTER = True
    elif operand_type == 'goto':
        ALLOW_NUMBER = True
        ALLOW_LABELS = True
    elif operand_type == 'jmp':
        ALLOW_NUMBER = True
        ALLOW_REGISTER = True
        ALLOW_LABELS = True
    else:
        raise ValueError(f"Unknown operand type {operand_type}. Expect 'src', 'dst', 'jmp' or 'goto'")

    try:
        num = int(tok, 0)
    except ValueError:
        pass
    else:
        if ALLOW_NUMBER:
            return to_u16(num), True
        else:
            raise ValueError(f"Number as operand is not allowed with {operand_type} operand type.")

    if tok in REGISTERS:
        if ALLOW_REGISTER:
            return to_u16(REGISTERS[tok]), False
        else:
            raise ValueError(f"Register as operand is not allowed with {operand_type} operand type.")

    if ALLOW_LABELS:
        return '#' + tok, True

    raise ValueError(f"Invalid operand {tok!r} for type {operand_type!r}")


def create_command(imm1: bool, imm2: bool, func: str) -> int:
    opcode, op_type, op_func = find_opcode_path(func)
    w = 0
    w |= (imm1 << IM1_BIT)
    w |= (imm2 << IM2_BIT)
    w |= (OPCODES[opcode] << OPCODE_SHIFT)
    w |= (TYPES[opcode][op_type] << SUBTYPE_SHIFT)
    w |= (FUNCS[opcode][op_type][op_func] << SUBFUNC_SHIFT)
    return to_u16(w)


def to_string(*inp) -> str:
    result = ""
    for element in inp:
        result = result + str(element) + " "
    result = result[:-1] + "\n"
    return result


def parse_multi(lines: list) -> str:
    parsed = []
    for line in lines:
        result = parse_line(line)
        if result:
            parsed.append(result)
    return ''.join(parsed)


def parse_line(line: str) -> str | None:
    global command_line

    parts = line.lower().split()
    op = parts[0]
    def _check_length(expect): check_length(parts, expect, op)

    match op:
        case "nop":
            w0 = create_command(False, False, op)
            return to_string(0, EMPTY, EMPTY, EMPTY)

        case "exit":
            w0 = create_command(False, False, op)
            return to_string(w0, EMPTY, EMPTY, EMPTY)

        case "mov":
            _check_length(3)
            src, imm1 = parse_operand(parts[1], 'src')
            dst, _ = parse_operand(parts[2], 'dst')
            w0 = create_command(imm1, False, op)
            return to_string(w0, src, EMPTY, dst)

        case "push":
            _check_length(2)
            src, imm1 = parse_operand(parts[1], 'src')
            w0 = create_command(imm1, False, op)
            return to_string(w0, src, EMPTY, EMPTY)

        case "pop":
            _check_length(2)
            dst, _ = parse_operand(parts[1], 'dst')
            w0 = create_command(False, False, op)
            return to_string(w0, EMPTY, EMPTY, dst)

        case "label":
            _check_length(2)
            label = parts[1]
            if label in labels:
                raise KeyError(f"Label {label} already in labels. Each label should appear once.")
            labels[label] = command_line
            return None

        case "jmp":
            _check_length(2)
            src, imm1 = parse_operand(parts[1], 'jmp')
            dst, _ = parse_operand('pc', 'dst')
            w0 = create_command(imm1, False, 'mov')
            return to_string(w0, src, EMPTY, dst)

        case op if op in CALC_CODES_ONE_ARG:
            _check_length(3)
            arg1, imm1 = parse_operand(parts[1], 'src')
            dst, _ = parse_operand(parts[2], 'dst')
            w0 = create_command(imm1, False, op)
            return to_string(w0, arg1, EMPTY, dst)

        case op if op in CALC_CODES_TWO_ARGS:
            _check_length(4)
            arg1, imm1 = parse_operand(parts[1], 'src')
            arg2, imm2 = parse_operand(parts[2], 'src')
            dst, _ = parse_operand(parts[3], 'dst')
            w0 = create_command(imm1, imm2, op)
            return to_string(w0, arg1, arg2, dst)

        case op if op in CONDITION_CODES:
            _check_length(4)
            arg1, imm1 = parse_operand(parts[1], 'src')
            arg2, imm2 = parse_operand(parts[2], 'src')
            value, _ = parse_operand(parts[3], 'goto')
            w0 = create_command(imm1, imm2, op,)
            return to_string(w0, arg1, arg2, value)

        case _:
            raise ValueError(f"Unknown opcode '{op}'")


def base_assemble_file(in_path: str, out_path: str):
    global error_counter
    with open(in_path, 'r', encoding='utf-8') as fin, \
            open(out_path, 'w', encoding='utf-8') as fout:
        global command_line
        for ln, line in enumerate(fin, 1):
            try:
                parsed = parse_line(line)
                if parsed:
                    command_line += 1
                    fout.write(parsed)

            except ValueError as e:
                increase_error_counter()
                print(f"Error while assemble: {ln}: {e}")
                continue


def resolve_labels(in_path: str, out_path: str):
    pattern = re.compile(r'#(\w+)')
    with open(in_path, 'r', encoding='utf-8') as fin, \
            open(out_path, 'w', encoding='utf-8') as fout:

        for line in fin:
            def _repl(m):
                key = m.group(1)
                try:
                    return str(labels[key])
                except KeyError:
                    increase_error_counter()
                    print(f"Label '{key}' not found in labels dict")

            new_line = pattern.sub(_repl, line)
            fout.write(new_line)


if __name__ == '__main__':

    clean_code(INPUT_FILE, CLEAN_FILE)
    unpack_macro_commands(CLEAN_FILE, RESOLVED_MACRO_FILE)

    base_assemble_file(RESOLVED_MACRO_FILE, LABELS_FILE)
    resolve_labels(LABELS_FILE, OUTPUT_FILE)

    print(labels)
