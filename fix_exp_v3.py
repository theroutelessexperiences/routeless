"""Fix the experiences_v3 template: normalize double CRLF and replace garbled emoji."""
import os

filepath = r'templates\marketplace\experiences_v3.html'

with open(filepath, 'rb') as f:
    raw = f.read()

# Show what bytes surround ðŸ" for diagnosis
# ðŸ" is: 0xC3 0xB0 0xC5 0xB8 0xE2 0x80 0x9D 0xC2 0x8D
# Let's find it
garbled = b'\xc3\xb0\xc5\xb8\xe2\x80\x9d\xc2\x8d'
garbled2 = b'\xc3\xb0\xc5\xb8\xe2\x80\x9c\xc2\x8d'  # variant

found = raw.find(garbled)
found2 = raw.find(garbled2)
print(f'garbled variant 1 at {found}, variant 2 at {found2}')

if found >= 0:
    print('Replacing variant 1...')
    raw = raw.replace(garbled, b'&#128205;')
if found2 >= 0:
    print('Replacing variant 2...')
    raw = raw.replace(garbled2, b'&#128205;')

# Normalize double CRLF
raw = raw.replace(b'\r\r\n', b'\n').replace(b'\r\n', b'\n').replace(b'\r', b'\n')

with open(filepath, 'wb') as f:
    f.write(raw)
print('Done.')
