import os

filepath = r'c:\Users\User\OneDrive - iitr.ac.in\project_01\web_v1\templates\marketplace\experience_detail_v3.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the specific broken endif tag
content = content.replace('{% if listing.review_count > 1 %}s{%\n                endif %}', '{% if listing.review_count > 1 %}s{% endif %}')
content = content.replace('{% if listing.review_count > 1 %}s{%\r\n                endif %}', '{% if listing.review_count > 1 %}s{% endif %}')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
