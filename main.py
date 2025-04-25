INPUT_FILE = 'C:/Users/1/Documents/TuringComplete/input.txt'
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
    'r6': 6,
    'r7': 7,
    'counter': 8,
    'sp': 9,
}

labels = {}
command_line = 0


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


def check_lenth(parts: list, expect: int, op: str):
    if len(parts) != expect:
        raise ValueError(f"{op} expects {expect - 1} operands, got {len(parts) - 1}")


def parse_operand(tok: str, operand_type: str = 'src') -> tuple[int, bool]:
    ALLOW_NUMBER = False
    ALLOW_REGISTER = False
    if operand_type == 'src':
        ALLOW_NUMBER = True
        ALLOW_REGISTER = True
    elif operand_type == 'dst':
        ALLOW_REGISTER = True
    elif operand_type == 'value':
        ALLOW_NUMBER = True
    else:
        raise ValueError(f"Unknown operand type {operand_type}. Expect 'src', 'dst' or 'value'")

    if ALLOW_NUMBER:
        try:
            num = int(tok, 0)
        except ValueError:
            pass
        else:
            return to_u16(num), True

    if ALLOW_REGISTER:
        if tok in REGISTERS:
            return REGISTERS[tok], False
        else:
            raise ValueError(f"Unknown register {tok!r}")

    raise ValueError(f"Invalid operand {tok!r} for type {operand_type!r}")


def create_command(imm1: bool, imm2: bool, func: str) -> int:
    opcode, op_type, op_func = find_opcode_path(func)
    w = 0
    w |= (imm1 << IM1_BIT)
    w |= (imm2 << IM2_BIT)
    w |= (OPCODES[opcode] << OPCODE_SHIFT)
    w |= (TYPES[opcode][op_type] << SUBTYPE_SHIFT)
    w |= (FUNCS[opcode][op_type][op_func] << SUBFUNC_SHIFT)
    return w


def parse_line(line: str) -> tuple[int, int, int, int] | None | str:
    global command_line

    code = line.split(';', 1)[0].strip()
    if not code:
        return None
    parts = code.lower().split()
    op = parts[0]

    match op:
        case "nop":
            return 0, EMPTY, EMPTY, EMPTY

        case "mov":
            check_lenth(parts, 3, op)
            src, imm1 = parse_operand(parts[1], 'src')
            dst, _ = parse_operand(parts[2], 'dst')
            w0 = create_command(imm1, False, op)
            return w0, src, EMPTY, dst

        case "push":
            check_lenth(parts, 2, op)
            src, imm1 = parse_operand(parts[1], 'src')
            w0 = create_command(imm1, False, op)
            return w0, src, EMPTY, EMPTY

        case "pop":
            check_lenth(parts, 2, op)
            dst, _ = parse_operand(parts[1], 'dst')
            w0 = create_command(False, False, op)
            return w0, EMPTY, EMPTY, dst

        case "label":
            label = parts[1]
            if label in labels:
                raise KeyError(f"Label {label} already in labels. Each label should appear once.")
            labels[label] = command_line
            return ''

        case op if op in CALC_CODES_ONE_ARG:
            check_lenth(parts, 3, op)
            arg1, imm1 = parse_operand(parts[1], 'src')
            dst, _ = parse_operand(parts[2], 'dst')
            w0 = create_command(imm1, False, op)
            return w0, arg1, EMPTY, dst

        case op if op in CALC_CODES_TWO_ARGS:
            check_lenth(parts, 4, op)
            arg1, imm1 = parse_operand(parts[1], 'src')
            arg2, imm2 = parse_operand(parts[2], 'src')
            dst, _ = parse_operand(parts[3], 'dst')
            w0 = create_command(imm1, imm2, op)
            return w0, arg1, arg2, dst

        case op if op in CONDITION_CODES:
            check_lenth(parts, 4, op)
            arg1, imm1 = parse_operand(parts[1], 'src')
            arg2, imm2 = parse_operand(parts[2], 'src')
            value, _ = parse_operand(parts[3], 'value')
            w0 = create_command(imm1, imm2, op,)
            return w0, arg1, arg2, value

        case _:
            raise ValueError(f"Unknown opcode '{op}'")


def base_assemble_file(in_path: str, out_path: str):
    with open(in_path, 'r', encoding='utf-8') as fin, \
            open(out_path, 'w', encoding='utf-8') as fout:
        global command_line
        for ln, line in enumerate(fin, 1):
            try:
                parsed = parse_line(line)
                if not parsed:
                    continue
                if len(parsed) == 4:
                    command_line += 1
                    w0, w1, w2, w3 = parsed
                    fout.write(f"{to_u16(w0)} {to_u16(w1)} {to_u16(w2)} {to_u16(w3)}\n")

            except ValueError as e:
                print(f"Ошибка в строке {ln}: {e}")
                continue


# def resolv_labels()


if __name__ == '__main__':
    base_assemble_file(INPUT_FILE, LABELS_FILE)
    print(f"Сборка завершена — результат в {OUTPUT_FILE}")
    print(labels)
