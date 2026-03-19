"""
Fix experiences_v3.html:
1. Remove BOM if present
2. Collapse multi-line {{ listing.category }} into one line
3. Fix garbled emoji chars
"""

filepath = r'templates\marketplace\experiences_v3.html'

with open(filepath, 'rb') as f:
    raw = f.read()

# Remove UTF-8 BOM if present
if raw.startswith(b'\xef\xbb\xbf'):
    print('Removing BOM...')
    raw = raw[3:]

# Also check for garbled pin emoji bytes (f0 9f 93 8d in latin-1 read as C3B0 C5B8 E2809D C28D)
# The ðŸ" is 4 bytes in UTF-8: 0xF0 0x9F 0x93 0x8D  
# When a file is read as latin-1 and re-encoded as UTF-8, it becomes: C3B0 C59F E2849B C28D
# Let's check what bytes we have:
idx = raw.find(b'\xc3\xb0')
print(f'Found \\xc3\\xb0 at byte {idx}')
if idx >= 0:
    print('Surrounding bytes:', raw[idx:idx+10].hex())

# Decode carefully
text = raw.decode('utf-8', errors='replace')

# Fix multi-line template variable in category badge (span)
# Pattern: ">{{ \n    listing.category }}<"  
# This could work fine in Django but might trip up browsers if the HTML is misread
import re
# Collapse "{{ \n    listing.category }}" into "{{ listing.category }}"  
text = re.sub(r'\{\{\s*\n\s*listing\.category\s*\}\}', '{{ listing.category }}', text)
# While we're at it fix any other multiline {{ ... }} patterns  
text = re.sub(r'\{\{\s*\n\s*([\w\.\|: ]+?)\s*\}\}', r'{{ \1 }}', text)

# Fix garbled rupee: â‚¹ → ₹
text = text.replace('â‚¹', '₹')
# Fix garbled pin emoji: ðŸ" → 📍  
text = text.replace('ðŸ"', '📍')
# Fix other common garbling: â€™ → '
text = text.replace('â€™', "'")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print('Done.')

# Also fix index.html
filepath2 = r'templates\marketplace\index.html'
with open(filepath2, 'r', encoding='utf-8', errors='replace') as f:
    text2 = f.read()
text2 = text2.replace('â‚¹', '₹')
text2 = text2.replace('ðŸ"', '📍')
text2 = re.sub(r'\{\{\s*\n\s*([\w\.\|: ]+?)\s*\}\}', r'{{ \1 }}', text2)
with open(filepath2, 'w', encoding='utf-8') as f:
    f.write(text2)
print('Fixed index.html too.')
