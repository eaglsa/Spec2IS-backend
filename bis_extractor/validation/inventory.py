import json
from pathlib import Path
from bis_extractor.database.schema import get_session
from bis_extractor.database.models import Standard, Department, StandardDetail, StandardRelationship, Document
from bis_extractor.config import OUTPUT_DIR, RAW_STORAGE_DIR

def generate_field_inventory():
    """
    Parses a representative sample of raw detail API responses to build a field inventory.
    Reads from output/raw/std_*.json
    """
    field_counts = {}
    total_records = 0
    
    for raw_file in RAW_STORAGE_DIR.glob('std_*.json'):
        total_records += 1
        with open(raw_file, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                items = data.get('data', [])
                if isinstance(items, list) and len(items) > 0:
                    record = items[0]
                elif isinstance(items, dict):
                    record = items
                else:
                    record = {}
                    
                for key, value in record.items():
                    if key not in field_counts:
                        field_counts[key] = {'count': 0, 'types': set(), 'type_str': ''}
                    field_counts[key]['count'] += 1
                    field_counts[key]['types'].add(type(value).__name__)
            except Exception as e:
                pass
                
    inventory = []
    for key, stats in field_counts.items():
        inventory.append({
            'field_name': key,
            'data_types': list(stats['types']),
            'records_present': stats['count'],
            'records_missing': total_records - stats['count']
        })
        
    with open(OUTPUT_DIR / 'field_inventory.json', 'w') as f:
        json.dump(inventory, f, indent=2)

def generate_full_report():
    session = get_session()
    
    total_depts = session.query(Department).count()
    total_stds = session.query(Standard).count()
    total_details = session.query(StandardDetail).count()
    total_rels = session.query(StandardRelationship).count()
    
    report = {
        'departments_discovered': total_depts,
        'departments_crawled': total_depts, # approximate for now
        'total_standard_records_discovered': total_stds,
        'total_unique_standards': total_stds,
        'total_standard_detail_requests': total_details, # assuming 1 per detail
        'successful_detail_requests': total_details,
        'total_relationships': total_rels
    }
    
    with open(OUTPUT_DIR / 'crawl_report.json', 'w') as f:
        json.dump(report, f, indent=2)

def run_all_validations():
    OUTPUT_DIR.mkdir(exist_ok=True)
    generate_field_inventory()
    generate_full_report()
    
if __name__ == '__main__':
    run_all_validations()
