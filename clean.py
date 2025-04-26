def clean_code(in_path: str, out_path: str):
    with open(in_path, 'r', encoding='utf-8') as fin, \
            open(out_path, 'w', encoding='utf-8') as fout:
        for line in fin:
            code = line.split(';', 1)[0].strip()
            if code:
                code = code.lower()
                fout.write(code + "\n")
