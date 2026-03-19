files = [
    r'templates\marketplace\experiences_v3.html',
    r'templates\marketplace\index.html',
    r'templates\marketplace\experience_detail_v3.html',
]
for filepath in files:
    with open(filepath, 'rb') as f:
        raw = f.read()
    # The garbled rupee in latin-1 decode of UTF-8 would show as: â‚¹ (bytes: e2 82 b9 -> c3 a2 c2 82 c2 b9)
    # Check for double-encoded bytes (UTF-8 of UTF-8)
    has_double_utf8 = b'\xc3\xa2\xc2\x82' in raw
    has_utf8_rupee = b'\xe2\x82\xb9' in raw
    has_utf8_pin_emoji = b'\xf0\x9f\x93\x8d' in raw
    has_bom = raw.startswith(b'\xef\xbb\xbf')
    print(filepath)
    print(f'  BOM: {has_bom}')
    print(f'  UTF-8 rupee sign (â‚¹): {has_utf8_rupee}')
    print(f'  UTF-8 📍 emoji: {has_utf8_pin_emoji}')
    print(f'  Double-encoded UTF-8: {has_double_utf8}')
    print()
