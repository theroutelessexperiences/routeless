"""
Fix experience_detail_v3.html which has \r\r\n double-carriage-return endings 
from a previous fix script that mixed \n into a \r\n file.

Also fix multi-line broken {{ variable }} spans.
"""
import re

filepath = r'templates\marketplace\experience_detail_v3.html'

with open(filepath, 'rb') as f:
    raw = f.read()

# Normalize all line endings: replace \r\r\n -> \r\n, then \r\n -> \n, then all \r -> \n
raw = raw.replace(b'\r\r\n', b'\n')
raw = raw.replace(b'\r\n', b'\n')
raw = raw.replace(b'\r', b'\n')

text = raw.decode('utf-8', errors='replace')

# Fix garbled chars
text = text.replace('â‚¹', '₹')
text = text.replace('ðŸ"', '📍')

# Collapse multi-line Django template var references {{ ... \n ... }}
# This will collapse things like:
#   {{ listing.category\n                 }}  -> {{ listing.category }}
text = re.sub(r'\{\{\s*\n\s*([\w\.\|:\-_" ]+?)\s*\}\}', r'{{ \1 }}', text)

# Also fix multi-line {{ ... \n ... }} that don't match (e.g. floatformat:1)
# using a more general approach
def collapse_multiline_tags(text):
    lines = text.split('\n')
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # If a line contains {{ but not matching }}, try to merge with next line
        open_count = line.count('{{')
        close_count = line.count('}}')
        if open_count > close_count and i + 1 < len(lines):
            # Merge this line with next (collapse whitespace at joint)
            merged = line.rstrip() + ' ' + lines[i+1].lstrip()
            result.append(merged)
            i += 2
        else:
            result.append(line)
            i += 1
    return '\n'.join(result)

text = collapse_multiline_tags(text)

with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

print('Done. Line endings normalized and multi-line {{ }} collapsed.')

# Verify no more \r\r\n
with open(filepath, 'rb') as f:
    raw2 = f.read()
if b'\r\r' in raw2:
    print('WARNING: Still has \\r\\r sequences!')
else:
    print('OK: No double carriage returns.')
