import httpx
import re

r = httpx.get('https://standards.bis.gov.in/main.8c9b31dc7b0425e8.js', verify=False)
text = r.text

methods = re.findall(r'[\'"]([a-zA-Z0-9/_-]*get[A-Z][a-zA-Z0-9]*)[\'"]', text)
with open('scratch/js_get_endpoints.txt', 'w') as f:
    for m in set(methods):
        f.write(f"{m}\n")
        
print("Saved to scratch/js_get_endpoints.txt")
