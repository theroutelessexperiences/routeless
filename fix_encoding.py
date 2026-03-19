"""
Fix garbled Unicode characters in template files.
The files contain double-encoded UTF-8 sequences:
  ðŸ" = garbled 📍 (U+1F4CD, pin emoji)
  â‚¹  = garbled ₹ (U+20B9, Indian rupee sign)

We replace them with clean HTML entities or the correct UTF-8 string.
"""

import os

FILES_TO_FIX = [
    r'templates\marketplace\experiences_v3.html',
    r'templates\marketplace\index.html',
    r'templates\marketplace\host_dashboard_v3.html',
    r'templates\marketplace\experience_detail_v3.html',
    r'templates\marketplace\my_bookings.html',
    r'templates\marketplace\checkout.html',
    r'templates\marketplace\leave_review.html',
]

REPLACEMENTS = [
    # garbled pin emoji -> pin emoji as HTML entity equiv (use text instead to be safe)
    (b'\xc3\xb0\xc5\xb8\xe2\x80\x9d\xc2\x8d', '&#128205;'.encode()),   # ðŸ"​ -> 📍
    (b'\xc3\xb0\xc5\xb8\xe2\x80\x9c\x8d', '&#128205;'.encode()),       # variant
    # garbled rupee sign -> HTML entity
    (b'\xc3\xa2\xc2\x82\xc2\xb9', '&#8377;'.encode()),   # â‚¹ -> ₹
]

# Simple text-based replacements that the view_file tool showed
TEXT_REPLACEMENTS = [
    ('ðŸ"', '📍'),
    ('â‚¹', '₹'),
    ('ðŸ" ', '📍 '),
]

for filepath in FILES_TO_FIX:
    if not os.path.exists(filepath):
        print(f'SKIP (not found): {filepath}')
        continue
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    changed = False
    for old, new in TEXT_REPLACEMENTS:
        if old in content:
            content = content.replace(old, new)
            changed = True
            print(f'  Fixed "{old}" -> "{new}" in {filepath}')
    
    if changed:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f'SAVED: {filepath}')
    else:
        print(f'OK (no garbled chars): {filepath}')
