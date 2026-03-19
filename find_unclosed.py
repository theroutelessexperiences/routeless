import re

with open(r'c:\Users\User\OneDrive - iitr.ac.in\project_01\web_v1\templates\marketplace\experience_detail_v3.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

if_stack = []
for i, line in enumerate(lines):
    if '{% if ' in line or '{% ifdef' in line or '{% ifequal' in line or '{% ifnotequal' in line:
        # count how many ifs
        ifs = len(re.findall(r'\{%\s*if\b', line))
        for _ in range(ifs):
            if_stack.append(i + 1)
        
        # some inline endifs might be on the same line
        endifs = len(re.findall(r'\{%\s*endif\b', line))
        for _ in range(endifs):
            if if_stack:
                if_stack.pop()
    elif '{% endif %}' in line or '{% endif}' in line or '{%endif%}' in line or '{% endif' in line:
        endifs = len(re.findall(r'\{%\s*endif\b', line))
        for _ in range(endifs):
            if if_stack:
                if_stack.pop()

print("Unclosed IFs opened on lines:", if_stack)
