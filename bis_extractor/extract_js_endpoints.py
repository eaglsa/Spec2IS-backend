import httpx
import re

r = httpx.get('https://standards.bis.gov.in/main.8c9b31dc7b0425e8.js', verify=False)
text = r.text

# Also check for relative API paths
api_calls = re.findall(r'[\'"]([a-zA-Z0-9-]+-service/[^\'"]+)[\'"]', text)
urls = re.findall(r'[\'"](https?://[^\'"]+)[\'"]', text)

with open('scratch/js_endpoints.txt', 'w') as f:
    f.write("--- API CALLS ---\n")
    for a in set(api_calls):
        f.write(f"{a}\n")
    f.write("\n--- URLS ---\n")
    for u in set(urls):
        f.write(f"{u}\n")
        
print("Saved to scratch/js_endpoints.txt")
