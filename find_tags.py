import re
with open('templates/marketplace/experience_detail_v3.html', 'r', encoding='utf-8') as f: lines = f.readlines()
stack = []
with open('trace.log', 'w', encoding='utf-8') as out:
    for i, line in enumerate(lines):
        for token in re.findall(r'{%\s*(if|for|block|endif|endfor|endblock)\b', line):
            if token in ('if', 'for', 'block'):
                stack.append((token, i+1))
                out.write(f'PUSH {token} at {i+1}\n')
            else:
                if not stack: out.write(f'Unmatched {token} at line {i+1}\n')
                else:
                    top = stack.pop()
                    expected = 'end' + top[0]
                    out.write(f'POP {token} at {i+1}, expected matches {top[0]} opened at {top[1]}\n')
