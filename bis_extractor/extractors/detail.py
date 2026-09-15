from bs4 import BeautifulSoup
from bis_extractor.database.repository import Repository

def extract_standard_details(html_or_json: str | dict, standard_id: int, repo: Repository):
    """
    Extracts all fields from standard detail page.
    Automatically identifies new fields in JSON.
    """
    if isinstance(html_or_json, dict):
        data = html_or_json.get('data', {})
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        elif isinstance(data, list):
            data = {}
        known_fields = [
            'division', 'technical_committee', 'committee_number', 'member_secretary',
            'standard_type', 'language', 'certification_status', 'mandatory_status',
            'reaffirmation', 'revision', 'amendment', 'supersedes', 'superseded_by',
            'degree_of_equivalence', 'group', 'sub_group', 'ministry', 'sdg',
            'short_title', 'ics_code', 'equivalent_standard', 'identical_standard',
            'summary', 'scope', 'publication_date', 'effective_date', 'withdrawal_date',
            'classification'
        ]
        
        detail_data = {}
        extra_fields = {}
        for k, v in data.items():
            if k in known_fields:
                detail_data[k] = v
            else:
                extra_fields[k] = v
                
        if extra_fields:
            detail_data['extra_fields'] = extra_fields
            
        repo.add_standard_detail(standard_id, detail_data)
        
    else:
        # Fallback for HTML
        soup = BeautifulSoup(html_or_json, 'html.parser')
        # Placeholder for dynamic field extraction from DOM
        detail_data = {}
        # ... logic to map generic rows to fields ...
        repo.add_standard_detail(standard_id, detail_data)
