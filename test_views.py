import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safar_hq.settings')
os.environ['DEBUG'] = 'True'
django.setup()

c = Client()
urls_to_test = [
    '/',
    '/experiences/',
    '/dashboard/host/',
]

from marketplace.models import Experience
exp = Experience.objects.first()
if exp:
    urls_to_test.append(f'/experiences/{exp.slug}/')

with open('crash_log2.html', 'w', encoding='utf-8') as f:
    for url in urls_to_test:
        try:
            response = c.get(url, SERVER_NAME='localhost')
            content = response.content.decode('utf-8')
            f.write(f"--- URL: {url} ---\n")
            f.write(content)
        except Exception as e:
            f.write(f"--- EXCEPTION ON {url} ---\n")
            import traceback
            f.write(traceback.format_exc())
            f.write("\n")
