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


def is_int(tok: str) -> bool:
    try:
        int(tok)
        return True
    except ValueError:
        return False


def is_register(tok: str) -> bool:
    return tok in REGISTERS


def is_int_or_register(tok: str) -> bool:
    return is_int(tok) or is_register(tok)


def is_condition(command, arg1, arg2):
    return (command in CONDITION_CODES
            and is_int_or_register(arg1)
            and is_int_or_register(arg2))
