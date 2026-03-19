import re

fp = r'templates\marketplace\experiences_v3.html'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the broken multi-line category option (lines 63-64 pattern)
# Pattern has pipes inside {% if %} which Django won't parse
content = re.sub(
    r'<option value="[{]{2} cat\|lower [}]{2}" [{]% if request\.GET\.category==cat\|lower %[}]selected[{]% endif %[}]>[{]{2}\s*cat\s*[}]{2}</option>',
    '<option value="{{ cat }}" {% if request.GET.category == cat %}selected{% endif %}>{{ cat }}</option>',
    content
)

# Also fix any remaining == without spaces around it for category
content = content.replace('request.GET.category==cat', 'request.GET.category == cat')

print("After fix, sample of category option area:")
idx = content.find('for cat in categories')
print(content[idx:idx+200])

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
