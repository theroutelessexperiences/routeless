import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safar_hq.settings')
django.setup()
from django.test import Client
c = Client(HTTP_HOST='127.0.0.1')
pages = [('/', 'Home'), ('/experiences/', 'Experiences List'), ('/experiences/riverside-camping/', 'Experience Detail')]
with open('missing_utf8.log', 'w', encoding='utf-8') as f:
    for url, name in pages:
        try:
            r = c.get(url)
            if r.status_code == 200:
                content = r.content.decode('utf-8')
                missing = [line.strip() for line in content.split('\n') if 'MISSING' in line]
                if missing:
                    f.write(f'\n--- {name} ({url}) ---\n')
                    for m in missing: f.write(m + '\n')
            else:
                f.write(f'{name} ({url}) returned {r.status_code}\n')
        except Exception as e:
            import traceback
            f.write(f'{name} ({url}) Failed: {e}\n')
            traceback.print_exc(file=f)
