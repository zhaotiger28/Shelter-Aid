"""
Web scraper module to find tax forms and economic impact reports on organization websites.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from typing import List, Dict, Optional
import mimetypes
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self, timeout=10, max_pages=20):
        self.timeout = timeout
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def find_documents(self, org_name: str, website: str) -> Dict[str, List[str]]:
        """
        Scrape website to find tax forms (990, 990-N) and economic impact reports.
        
        Returns:
            {
                'tax_forms': ['url1', 'url2'],
                'annual_reports': ['url1'],
                'impact_reports': ['url1'],
                'other_financial': ['url1']
            }
        """
        results = {
            'tax_forms': [],
            'annual_reports': [],
            'impact_reports': [],
            'other_financial': []
        }
        
        try:
            if not website.startswith(('http://', 'https://')):
                website = f'https://{website}'
            
            # Ensure SSL verification is not blocking legitimate sites
            visited = set()
            to_visit = [website]
            pages_crawled = 0
            
            while to_visit and pages_crawled < self.max_pages:
                url = to_visit.pop(0)
                
                if url in visited:
                    continue
                visited.add(url)
                
                try:
                    response = self.session.get(url, timeout=self.timeout, verify=False)
                    response.raise_for_status()
                    pages_crawled += 1
                    
                    # Parse the page
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for links to documents
                    for link in soup.find_all('a', href=True):
                        href = link.get('href')
                        text = link.get_text().lower()
                        
                        if not href:
                            continue
                        
                        full_url = urljoin(url, href)
                        
                        # Skip if already found
                        if full_url in visited:
                            continue
                        
                        # Check if it's a PDF or relevant page
                        if href.lower().endswith('.pdf'):
                            if any(term in href.lower() for term in ['990', 'form', 'tax']):
                                results['tax_forms'].append(full_url)
                            elif any(term in href.lower() for term in ['annual', 'report']):
                                results['annual_reports'].append(full_url)
                            elif any(term in href.lower() for term in ['impact', 'economic']):
                                results['impact_reports'].append(full_url)
                            else:
                                results['other_financial'].append(full_url)
                        
                        # Check link text
                        if any(term in text for term in ['990', 'form', 'tax', 'irs']):
                            if full_url not in results['tax_forms'] and full_url not in visited:
                                to_visit.append(full_url)
                        elif any(term in text for term in ['annual report', 'year end report']):
                            if full_url not in results['annual_reports'] and full_url not in visited:
                                to_visit.append(full_url)
                        elif any(term in text for term in ['impact report', 'economic impact', 'effectiveness']):
                            if full_url not in results['impact_reports'] and full_url not in visited:
                                to_visit.append(full_url)
                        
                        # Add internal links to queue
                        try:
                            link_domain = urlparse(full_url).netloc
                            base_domain = urlparse(website).netloc
                            if link_domain == base_domain and full_url not in visited:
                                to_visit.append(full_url)
                        except:
                            pass
                    
                    time.sleep(0.5)  # Be respectful to servers
                
                except Exception as e:
                    logger.warning(f"Error processing {url}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error scraping {website}: {e}")
        
        # Remove duplicates
        for key in results:
            results[key] = list(set(results[key]))
        
        logger.info(f"Found documents for {org_name}: {results}")
        return results

    def fetch_document(self, url: str) -> Optional[bytes]:
        """Fetch a document (PDF or HTML) from URL."""
        try:
            response = self.session.get(url, timeout=self.timeout, verify=False)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            import pdfplumber
            import io
            
            text = ""
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            return ""


def main():
    # Example usage
    scraper = WebScraper()
    
    # Example organization
    results = scraper.find_documents("Sample Org", "example.org")
    print("Found documents:", results)


if __name__ == "__main__":
    main()
