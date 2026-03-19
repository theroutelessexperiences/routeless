"""
Apply the same fixes to all remaining template files:
- Remove BOM
- Collapse any remaining multi-line {{ variable }} tags
- Fix garbled emoji/rupee chars
"""
import re, os

FILES = [
    r'templates\marketplace\experience_detail_v3.html',
    r'templates\marketplace\host_dashboard_v3.html',
    r'templates\marketplace\my_bookings.html',
    r'templates\marketplace\checkout.html',
    r'templates\marketplace\leave_review.html',
    r'templates\base.html',
]

for filepath in FILES:
    if not os.path.exists(filepath):
        print(f'SKIP: {filepath}')
        continue

    with open(filepath, 'rb') as f:
        raw = f.read()

    # Remove BOM
    had_bom = raw.startswith(b'\xef\xbb\xbf')
    if had_bom:
        raw = raw[3:]
        print(f'Removed BOM: {filepath}')

    text = raw.decode('utf-8', errors='replace')

    original = text

    # Fix garbled chars
    text = text.replace('â‚¹', '₹')
    text = text.replace('ðŸ"', '📍')

    # Collapse multi-line {{ var }} patterns that cross only one line break
    text = re.sub(r'\{\{\s*\n\s*([\w\.\|:\-_" ]+?)\s*\}\}', r'{{ \1 }}', text)

    if text != original or had_bom:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f'Fixed: {filepath}')
    else:
        print(f'No changes: {filepath}')
