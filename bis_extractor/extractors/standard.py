from bis_extractor.database.repository import Repository

def extract_standards(data: dict, department_id: str, repo: Repository):
    """
    Extracts standard listings from JSON API response.
    """
    items = data.get('data', [])
    if not items:
        return 0

    for item in items:
        std_number = item.get('standardNumber', '')
        if ':' in std_number:
            parts = std_number.rsplit(':', 1)
            is_num = parts[0].strip()
            year = parts[1].strip()
        else:
            is_num = std_number
            year = ''
            
        repo.add_standard(
            department_id=department_id,
            is_number=is_num,
            year=year,
            title=item.get('standardName', ''),
            status='Published', # Default to published since this is from published standards list
            url=f"https://standards.bis.gov.in/website/published-standards/standard-details?standardId={item.get('standardEncId')}",
            encrypted_id=item.get('standardEncId', ''),
            bis_standard_id=item.get('standardId')
        )
    return len(items)
