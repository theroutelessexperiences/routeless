import os

filepath = r'c:\Users\User\OneDrive - iitr.ac.in\project_01\web_v1\templates\marketplace\experience_detail_v3.html'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix location references (now a plain CharField like "Manali, Himachal Pradesh")
content = content.replace('listing.location.slug }}', 'listing.location|lower }}')
content = content.replace('listing.location.name }},', 'listing.location }},')
content = content.replace('{{listing.location.name }}', '{{ listing.location }}')
content = content.replace('{{ listing.location.name }}', '{{ listing.location }}')
content = content.replace('listing.location.state}}', 'listing.location }}')
content = content.replace('listing.location.state }},', 'listing.location }},') # removes duplicate if combined

# Fix category references (now a plain CharField)
content = content.replace('{{ listing.category.icon }}', 'bi-tag-fill')
content = content.replace('{{listing.category.name}}', '{{ listing.category }}')
content = content.replace('{{ listing.category.name}}', '{{ listing.category }}')
content = content.replace('listing.category.name}}', 'listing.category }}')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done.")
