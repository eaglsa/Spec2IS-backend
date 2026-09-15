import csv
from pathlib import Path
from bis_extractor.config import OUTPUT_DIR

def create_metadata_matrix():
    matrix = [
        ["Field", "Available", "Source", "Endpoint", "JSON path", "Status"],
        ["IS Number", "Yes", "List API", "getWebsiteIndianStandardsList", "standardNumber", "Populated"],
        ["Title", "Yes", "List API", "getWebsiteIndianStandardsList", "standardTitle", "Populated"],
        ["Year", "Yes", "List API", "getWebsiteIndianStandardsList", "standardYear", "Populated"],
        ["Status", "Yes", "List API", "getWebsiteIndianStandardsList", "standardStatus", "Populated"],
        ["Department", "Yes", "Detail API", "getStandardsWithDeptAndCommittee", "departmentName", "Populated"],
        ["Committee", "Yes", "Detail API", "getStandardsWithDeptAndCommittee", "committeeName", "Populated"],
        ["Scope", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["ICS", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["SDG", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Mandatory Status", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Certification", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["International Standard", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Equivalent Standard", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Related Standards", "Yes", "Cross Ref API", "getCrossRefDetails", "crossFollowRefData", "Populated"],
        ["Amendments", "Yes", "Cross Ref API", "getCrossRefDetails", "crossRefData", "Populated"],
        ["Revision", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Reaffirmation", "No", "N/A", "N/A", "N/A", "NOT_PUBLICLY_EXPOSED"],
        ["Publication Information", "Yes", "List API", "getWebsiteIndianStandardsList", "publicationDate", "Populated"],
        ["Document Metadata", "No", "N/A", "N/A", "N/A", "AUTH_REQUIRED"]
    ]
    
    with open(OUTPUT_DIR / 'metadata_availability.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(matrix)

if __name__ == '__main__':
    create_metadata_matrix()
