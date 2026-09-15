import logging
import json
import traceback
from bis_extractor.database.repository import Repository
from bis_extractor.crawler.http import HttpClient
from bis_extractor.crawler.rate_limit import rate_limiter
from bis_extractor.storage.raw import save_raw_response
from bis_extractor.extractors.standard import extract_standards
from bis_extractor.extractors.detail import extract_standard_details
from bis_extractor.database.models import Department, Standard

logger = logging.getLogger(__name__)

class CrawlEngine:
    def __init__(self, repo: Repository, http: HttpClient):
        self.repo = repo
        self.http = http

    def crawl_department(self, dept_name: str):
        dept = self.repo.session.query(Department).filter_by(name=dept_name).first()
        if not dept:
            logger.error(f"Department {dept_name} not found. Run discover first.")
            return

        logger.info(f"Crawling standards for department: {dept.name}")
        
        # Pagination loop
        page = 0
        size = 100
        has_more = True
        
        url = "https://standardsadmin.bis.gov.in/proposal-service/getWebsiteIndianStandardsList"
        
        while has_more:
            rate_limiter.wait()
            payload = {"departmentId": int(dept.department_id), "page": page, "size": size}
            
            try:
                res = self.http.post(url, json=payload)
                data = res.json()
                
                save_raw_response(url, data, f"dept_{dept.department_id}_page_{page}")
                
                items = data.get('data', [])
                if not items:
                    has_more = False
                    break
                    
                extract_standards(data, dept.department_id, self.repo)
                
                # Use hasMore from API if present, otherwise default to items length
                if 'hasMore' in data:
                    has_more = data['hasMore']
                    # Some APIs return string "true" or "false"
                    if isinstance(has_more, str):
                        has_more = has_more.lower() == 'true'
                else:
                    if len(items) < size:
                        has_more = False
                
                logger.info(f"Page {page} complete. has_more: {has_more}, items: {len(items)}")
                page += 1
            except Exception as e:
                logger.error(f"Failed to crawl department standards page {page}: {e}")
                has_more = False

        # Now crawl details for all standards in this department
        standards = self.repo.session.query(Standard).filter_by(department_id=dept.department_id).all()
        logger.info(f"Found {len(standards)} standards. Crawling details...")
        
        for std in standards:
            self.crawl_standard_detail(std)

    def crawl_standard_detail(self, std: Standard):
        if not std.bis_standard_id:
            logger.warning(f"Standard {std.is_number} missing bis_standard_id, skipping detail crawl.")
            return

        detail_url = "https://standardsadmin.bis.gov.in/proposal-service/getStandardsWithDeptAndCommittee"
        rate_limiter.wait()
        
        try:
            res = self.http.post(detail_url, json={"StandardId": std.bis_standard_id})
            data = res.json()
            save_raw_response(detail_url, data, f"std_{std.bis_standard_id}")
            
            extract_standard_details(data, std.id, self.repo)
            
            # also fetch cross references
            cross_url = "https://standardsadmin.bis.gov.in/review-service/getCrossRefDetails"
            res_cross = self.http.post(cross_url, json={"StandardId": std.bis_standard_id})
            cross_data = res_cross.json()
            save_raw_response(cross_url, cross_data, f"cross_{std.bis_standard_id}")
            
            self._extract_relationships(cross_data, std.id)
            
            # log success
            self.repo.update_crawl_log(std.url, 'completed')
        except Exception as e:
            logger.error(f"Failed standard {std.is_number}: {e}")
            self.repo.update_crawl_log(std.url, 'failed', str(e))

    def _extract_relationships(self, data: dict, std_id: int):
        refs = data.get('data', {}).get('crossRefData', [])
        for r in refs:
            target = r.get('standardNumber', '')
            if not target:
                continue
            # Relationship type is often missing or called something else, we use "refers_to" as default
            rel_type = r.get('crossReferenceType', 'refers_to')
            
            self.repo.add_relationship(std_id, target, rel_type, raw_text=str(r))
            
        follows = data.get('data', {}).get('crossFollowRefData', [])
        for f in follows:
            target = f.get('standardNumber', '')
            if not target:
                continue
            rel_type = f.get('crossReferenceType', 'related_to')
            self.repo.add_relationship(std_id, target, rel_type, raw_text=str(f))

