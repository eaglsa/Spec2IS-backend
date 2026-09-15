from bs4 import BeautifulSoup
from bis_extractor.database.repository import Repository

def extract_departments(html_or_json: str | dict, repo: Repository):
    """
    Extracts departments from the source response.
    Specifically parses the native JSON API payload from the BIS backend.
    """
    if isinstance(html_or_json, dict):
        # Specific JSON API extraction logic for getWebsiteTechnicalDepartments
        departments = html_or_json.get('data', [])
        for dept in departments:
            dept_id = str(dept.get('departmentId', ''))
            dept_name = dept.get('deptName', '')
            dept_alias = dept.get('deptAliasName', '')
            
            repo.add_department(
                department_id=dept_id,
                name=dept_name,
                url=f"https://standards.bis.gov.in/website/published-standards/department-wise?departmentId={dept_id}"
            )
    else:
        # HTML fallback
        soup = BeautifulSoup(html_or_json, 'html.parser')
        # Placeholder logic: find specific links or elements
        for link in soup.find_all('a', class_='department-link'):
            dept_name = link.text.strip()
            dept_url = link['href']
            repo.add_department(department_id=dept_url, name=dept_name, url=dept_url)
