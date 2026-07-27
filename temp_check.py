import codecs

with codecs.open('Invoke-ITDiagnostic.ps1', 'r', encoding='utf-8') as f:
    lines = f.readlines()

brace_level = 0
in_string = False
in_single_string = False

for i, line in enumerate(lines):
    idx = 0
    while idx < len(line):
        if line[idx] == '`':
            idx += 2
            continue
            
        if in_string:
            if line[idx] == '"':
                in_string = False
        elif in_single_string:
            if line[idx] == "'":
                in_single_string = False
        else:
            if line[idx] == '"':
                in_string = True
            elif line[idx] == "'":
                in_single_string = True
            elif line[idx] == '{':
                brace_level += 1
            elif line[idx] == '}':
                brace_level -= 1
                if brace_level < 0:
                    print(f"Extra closing brace at line {i+1}: {line.strip()}")
        idx += 1

print(f"Final brace level: {brace_level}")
