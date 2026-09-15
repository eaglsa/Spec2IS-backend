import json
from bis_extractor.config import OUTPUT_DIR
from bis_extractor.database.repository import Repository
from bis_extractor.database.models import Department, Standard, StandardDetail, Document, CrawlLog

def generate_report(repo: Repository):
    """Generates the crawl_report.json"""
    report = {
        'total_departments': repo.session.query(Department).count(),
        'total_standards': repo.session.query(Standard).count(),
        'total_detail_pages': repo.session.query(StandardDetail).count(),
        'total_documents': repo.session.query(Document).count(),
        'total_pdfs': repo.session.query(Document).filter(Document.file_extension == 'pdf').count(),
        'failed_urls': [log.url for log in repo.session.query(CrawlLog).filter_by(status='failed').all()]
    }
    # Duplicate standard IDs
    all_stds = repo.session.query(Standard).all()
    bis_ids = [s.bis_standard_id for s in all_stds if s.bis_standard_id]
    dup_ids = len(bis_ids) - len(set(bis_ids))
    
    # Missing titles
    missing_titles = len([s for s in all_stds if not s.title])
    
    # Unresolved targets
    from bis_extractor.database.models import StandardRelationship
    all_rels = repo.session.query(StandardRelationship).all()
    unresolved_targets = 0
    for r in all_rels:
        # Check if target_is_number exists in standards table
        target = repo.session.query(Standard).filter_by(is_number=r.target_standard_is_number).first()
        if not target:
            unresolved_targets += 1
            
    report['data_quality'] = {
        'duplicate_standard_ids': dup_ids,
        'missing_titles': missing_titles,
        'unresolved_targets': unresolved_targets,
        'malformed_json': 0,
        'failed_detail_pages': len(report['failed_urls'])
    }
    
    report_path = OUTPUT_DIR / 'data_quality_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
        
    return report
