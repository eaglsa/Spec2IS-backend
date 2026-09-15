import json
import csv
import logging
from bis_extractor.database.models import Standard, StandardDetail, Department, Document, StandardRelationship
from bis_extractor.database.schema import get_session

logger = logging.getLogger(__name__)

def export_data(output_dir="output"):
    session = get_session()
    
    # Export departments
    depts = session.query(Department).all()
    with open(f"{output_dir}/departments.json", "w") as f:
        json.dump([d.__dict__ for d in depts], f, default=str)
        
    # Export standards
    standards = session.query(Standard).all()
    
    with open(f"{output_dir}/standards.json", "w") as f:
        # Avoid circular ref in dict
        data = []
        for s in standards:
            d = {c.name: getattr(s, c.name) for c in s.__table__.columns}
            if s.details:
                d['details'] = {c.name: getattr(s.details, c.name) for c in s.details.__table__.columns}
            data.append(d)
        json.dump(data, f, default=str)
        
    # Export CSVs
    import pandas as pd
    
    # Departments CSV
    pd.DataFrame([d.__dict__ for d in depts]).drop('_sa_instance_state', axis=1, errors='ignore').to_csv(f"{output_dir}/departments.csv", index=False)
    
    # Standards CSV
    std_df = pd.DataFrame([s.__dict__ for s in standards]).drop('_sa_instance_state', axis=1, errors='ignore')
    std_df.to_csv(f"{output_dir}/standards.csv", index=False)
    
    # Relationships CSV
    rels = session.query(StandardRelationship).all()
    pd.DataFrame([r.__dict__ for r in rels]).drop('_sa_instance_state', axis=1, errors='ignore').to_csv(f"{output_dir}/relationships.csv", index=False)
    
    # Create Excel
    try:
        with pd.ExcelWriter(f"{output_dir}/bis_standards.xlsx") as writer:
            pd.DataFrame([d.__dict__ for d in depts]).drop('_sa_instance_state', axis=1, errors='ignore').to_excel(writer, sheet_name='Departments', index=False)
            std_df.to_excel(writer, sheet_name='Standards', index=False)
            pd.DataFrame([r.__dict__ for r in rels]).drop('_sa_instance_state', axis=1, errors='ignore').to_excel(writer, sheet_name='Relationships', index=False)
            pd.DataFrame([d.__dict__ for d in session.query(Document).all()]).drop('_sa_instance_state', axis=1, errors='ignore').to_excel(writer, sheet_name='Documents', index=False)
    except Exception as e:
        logger.error(f"Failed to generate Excel: {e}")
        
    logger.info("Exported JSON, CSV, and Excel formats successfully.")
