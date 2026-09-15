import logging
from bis_extractor.crawler.rate_limit import rate_limiter
from bis_extractor.crawler.http import HttpClient
from bis_extractor.database.repository import Repository
from bis_extractor.storage.raw import save_raw_response
from bis_extractor.extractors.department import extract_departments

logger = logging.getLogger(__name__)

class Discoverer:
    def __init__(self, repo: Repository, http_client: HttpClient):
        self.repo = repo
        self.http = http_client

    def discover_departments(self):
        """Discover all departments using the exact mapped hidden API endpoint."""
        api_url = "https://standardsadmin.bis.gov.in/project-service/getWebsiteTechnicalDepartments"
        logger.info(f"Fetching departments natively from mapped API: {api_url}")
        
        rate_limiter.wait()
        
        try:
            response = self.http.post(api_url, json={})
            data = response.json()
            
            # Save raw JSON for resumability and audit
            save_raw_response(api_url, data, "department_list")
            
            # Parse JSON natively
            extract_departments(data, self.repo)
            
            # Also log for detailed crawl queue if necessary
            self.repo.add_crawl_log(api_url, "department_list")
            
            logger.info("Successfully discovered and parsed departments natively.")
        except Exception as e:
            logger.error(f"Failed to discover departments: {str(e)}")
        
    def discover_standard_details(self, standard_url: str):
        """Queue standard detail pages."""
        self.repo.add_crawl_log(standard_url, "standard_detail")
