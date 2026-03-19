"""
Final emoji fix: find the garbled pin emoji bytes and replace with HTML entity.
The garbled 'ðŸ"' is: UTF-8 bytes c3b0 c5b8 e2 80 9d c2 8d  
which is the result of reading a 4-byte emoji (f0 9f 93 8d) 
through latin-1 and then re-encoding as UTF-8.
"""

filepath = r'templates\marketplace\experiences_v3.html'

with open(filepath, 'rb') as f:
    raw = f.read()

print("File size:", len(raw))

# Print surrounding bytes to diagnose
# Look for 0xc3 0xb0 which starts the garbled sequence
positions = []
i = 0
while i < len(raw) - 1:
    if raw[i] == 0xc3 and raw[i+1] == 0xb0:
        positions.append(i)
    i += 1

print(f"Found {len(positions)} potential garbled emoji position(s).")
for pos in positions[:3]:
    hexstr = raw[pos:pos+12].hex()
    print(f"  at {pos}: {hexstr}")
    try:
        snippet = raw[pos:pos+12].decode('utf-8', errors='replace')
        print(f"  decoded: {repr(snippet)}")
    except:
        pass

# Try each known garbled variant  
garbled_variants = [
    bytes.fromhex('c3b0c5b8e2809dc28d'),   # variant 1
    bytes.fromhex('c3b0c5b8e2809cc28d'),   # variant 2 
    bytes.fromhex('c3b0c5b8e280a2c28d'),   # variant 3
]

replacement = b'&#128205;'
fixed = False
for variant in garbled_variants:
    if variant in raw:
        raw = raw.replace(variant, replacement)
        print(f"Replaced variant: {variant.hex()}")
        fixed = True

# Also try exact bytes from positions found
for pos in positions:
    # Take 8 bytes from this position
    candidate = raw[pos:pos+8] 
    if candidate not in garbled_variants and candidate not in [replacement[:8]]:
        print(f"Trying candidate: {candidate.hex()}")
        if b'\x93' in candidate or b'\x8d' in candidate:
            raw = raw.replace(raw[pos:pos+8], replacement)
            print(f"Replaced at position {pos}")
            fixed = True
            break

if not fixed:
    print("Could not find and replace garbled emoji bytes.")
    print("Trying text-mode replacement...")
    text = raw.decode('utf-8', errors='replace')
    text = text.replace('\udcf0\udcb8\udc9d\udcc2\udc8d', '&#128205;')
    text = text.replace('\ufffd\ufffd\ufffd\ufffd', '')
    raw = text.encode('utf-8')

with open(filepath, 'wb') as f:
    f.write(raw)

print("Done. File saved.")
