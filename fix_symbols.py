import os

replacements = {
    'Ã—': '&times;',
    'â€˜': '&lsquo;',
    'â€™': '&rsquo;',
    'â€œ': '&ldquo;',
    'â€ ': '&rdquo;',
    'â€¢': '&bull;',
    'â€“': '&ndash;',
    'â€”': '&mdash;',
    'Â©': '&copy;',
    'â‚¹': '&#8377;'
}

template_dir = r'c:\Users\User\OneDrive - iitr.ac.in\project_01\routeless\templates'
count = 0
for root, dirs, files in os.walk(template_dir):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
                
            original = content
            for k, v in replacements.items():
                content = content.replace(k, v)
                
            if content != original:
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(content)
                print(f'Fixed {path}')
                count += 1
print(f'Replaced in {count} files.')
