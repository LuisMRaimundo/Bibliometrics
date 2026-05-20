import os, requests
MAIL = os.environ.get('MAIL') or "luisraimundo@fsch.unl.pt"
r = requests.get('https://api.openalex.org/works',
                 params={'per_page': 1, 'mailto': MAIL},
                 timeout=30)
print('status:', r.status_code)
print('ok_json:', (r.ok and ('results' in r.json())))
