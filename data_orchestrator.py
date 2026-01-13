"""
Orchestrator module: Coordinates web scraping, data extraction, validation, and CSV generation.
Main entry point for automated org data collection.
"""

import csv
import logging
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
import time

from web_scraper import WebScraper
from gemini_extractor import GeminiExtractor
from data_validator import DataValidator
import algov1

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OrganizationDataCollector:
    """
    Automated data collection for organizations.
    Takes org name + website, finds documents, extracts metrics, validates, and generates CSV.
    """
    
    def __init__(self, gemini_api_key: str, cache_dir: str = "./extraction_cache"):
        """Initialize collector."""
        self.gemini_api_key = gemini_api_key
        self.scraper = WebScraper(timeout=15, max_pages=25)
        self.extractor = GeminiExtractor(gemini_api_key)
        self.validator = DataValidator()
        self.cache_dir = cache_dir
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, org_name: str) -> str:
        """Get cache file path for organization."""
        safe_name = org_name.replace(" ", "_").replace("/", "_").lower()
        return os.path.join(self.cache_dir, f"{safe_name}_extraction.json")

    def _load_from_cache(self, org_name: str) -> Optional[Dict]:
        """Load cached extraction data."""
        cache_path = self._get_cache_path(org_name)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    logger.info(f"Loading cached data for {org_name}")
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {org_name}: {e}")
        return None

    def _save_to_cache(self, org_name: str, data: Dict) -> None:
        """Save extraction data to cache."""
        cache_path = self._get_cache_path(org_name)
        try:
            with open(cache_path, 'w') as f:
                json.dump(data, f, indent=2)
                logger.info(f"Cached data for {org_name}")
        except Exception as e:
            logger.warning(f"Failed to cache data for {org_name}: {e}")

    def collect_organization_data(self, org_name: str, website: str, use_cache: bool = True) -> Dict:
        """
        Complete pipeline: scrape -> extract -> validate -> return metrics.
        
        Returns: {
            'org_name': str,
            'website': str,
            'extracted_data': {},
            'normalized_metrics': {finance, supply, population, urgency, capacity},
            'validation_results': {},
            'quality_score': float,
            'documents_found': {},
            'status': 'success' | 'partial' | 'failed'
        }
        """
        
        result = {
            'org_name': org_name,
            'website': website,
            'extracted_data': None,
            'normalized_metrics': None,
            'validation_results': None,
            'quality_score': 0,
            'documents_found': None,
            'status': 'in-progress',
            'timestamp': datetime.now().isoformat(),
            'errors': []
        }
        
        try:
            # Check cache
            if use_cache:
                cached = self._load_from_cache(org_name)
                if cached:
                    return cached
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Starting collection for: {org_name}")
            logger.info(f"Website: {website}")
            logger.info(f"{'='*60}")
            
            # Step 1: Scrape website
            logger.info("[1/4] Scraping website for documents...")
            documents = self.scraper.find_documents(org_name, website)
            result['documents_found'] = documents
            
            # Step 2: Extract data
            logger.info("[2/4] Extracting data from documents...")
            extracted_data = self._extract_from_documents(org_name, documents)
            result['extracted_data'] = extracted_data
            
            if not extracted_data or all(v is None for v in extracted_data.values() if k != 'confidence_scores' for k in ['annual_revenue', 'population_served', 'total_expenses']):
                logger.warning(f"No data extracted for {org_name}")
                result['status'] = 'partial'
            else:
                result['status'] = 'success'
            
            # Step 3: Validate data
            logger.info("[3/4] Validating extracted data...")
            validation_results = self.validator.validate_all(extracted_data)
            result['validation_results'] = {k: v[1] for k, v in validation_results.items()}  # Store just messages
            self.validator.log_validation_results(org_name, validation_results)
            
            # Calculate quality score
            quality_score = self.validator.get_data_quality_score(extracted_data, validation_results)
            result['quality_score'] = quality_score
            logger.info(f"Data Quality Score: {quality_score:.1%}")
            
            # Step 4: Normalize metrics
            logger.info("[4/4] Normalizing metrics...")
            normalized = self.extractor.normalize_metrics(extracted_data)
            result['normalized_metrics'] = normalized
            
            # Log results
            logger.info(f"Results for {org_name}:")
            logger.info(f"  Finance: {normalized['finance']:.2f}")
            logger.info(f"  Supply: {normalized['supply']:.2f}")
            logger.info(f"  Population: {normalized['population']:.2f}")
            logger.info(f"  Urgency: {normalized['urgency']:.2f}")
            logger.info(f"  Capacity: {normalized['capacity']:.2f}")
            
            # Cache results
            self._save_to_cache(org_name, result)
            
        except Exception as e:
            logger.error(f"Error collecting data for {org_name}: {e}")
            result['status'] = 'failed'
            result['errors'].append(str(e))
        
        return result

    def _extract_from_documents(self, org_name: str, documents: Dict) -> Dict:
        """Extract data from found documents."""
        all_extracted = {}
        
        # Try to extract from each type of document
        for doc_type, urls in documents.items():
            if not urls:
                continue
            
            logger.info(f"  Processing {len(urls)} {doc_type}...")
            
            for url in urls[:3]:  # Limit to 3 per type for cost/speed
                try:
                    content = self.scraper.fetch_document(url)
                    if not content:
                        continue
                    
                    # Determine document type and extract
                    if url.lower().endswith('.pdf'):
                        extracted = self.extractor.extract_from_pdf(content, org_name)
                    else:
                        try:
                            text = content.decode('utf-8')
                            extracted = self.extractor.extract_from_text(text, org_name)
                        except:
                            extracted = self.extractor.extract_from_html(content.decode('utf-8', errors='ignore'), org_name)
                    
                    # Merge extracted data (prioritize more recent/complete data)
                    if extracted and any(extracted.get(k) for k in ['annual_revenue', 'population_served', 'total_expenses']):
                        all_extracted = extracted
                        logger.info(f"    Extracted from: {url[:80]}...")
                        break
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"    Error processing {url}: {e}")
        
        return all_extracted or self.extractor._empty_result()

    def process_org_list(self, csv_path: str, output_path: str = None, use_cache: bool = True) -> str:
        """
        Process CSV with columns: org_name, website
        Generates enriched CSV with extracted metrics.
        """
        if not output_path:
            output_path = csv_path.replace('.csv', '_enriched.csv')
        
        logger.info(f"Processing organization list: {csv_path}")
        
        organizations = []
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                organizations = list(reader)
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            return None
        
        # Collect data for all organizations
        enriched_data = []
        for i, org in enumerate(organizations, 1):
            org_name = org.get('org_name') or org.get('name') or org.get('organization')
            website = org.get('website') or org.get('url')
            
            if not org_name or not website:
                logger.warning(f"Skipping row {i}: missing org_name or website")
                continue
            
            logger.info(f"\n[{i}/{len(organizations)}] Processing: {org_name}")
            
            result = self.collect_organization_data(org_name, website, use_cache=use_cache)
            enriched_data.append(result)
            
            # Add delay between requests
            time.sleep(2)
        
        # Write enriched CSV
        self._write_enriched_csv(enriched_data, output_path)
        
        # Generate ranking using algov1
        self._generate_ranking(output_path)
        
        return output_path

    def _write_enriched_csv(self, enriched_data: List[Dict], output_path: str) -> None:
        """Write enriched data to CSV."""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'name', 'website', 'finance', 'supply', 'population', 'urgency', 'capacity',
                    'status', 'quality_score', 'annual_revenue', 'total_expenses', 
                    'population_served', 'employees', 'data_quality'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for org_result in enriched_data:
                    row = {
                        'name': org_result['org_name'],
                        'website': org_result['website'],
                        'status': org_result['status'],
                        'quality_score': f"{org_result['quality_score']:.2%}",
                        'finance': org_result['normalized_metrics']['finance'] if org_result['normalized_metrics'] else 0,
                        'supply': org_result['normalized_metrics']['supply'] if org_result['normalized_metrics'] else 0,
                        'population': org_result['normalized_metrics']['population'] if org_result['normalized_metrics'] else 0,
                        'urgency': org_result['normalized_metrics']['urgency'] if org_result['normalized_metrics'] else 0,
                        'capacity': org_result['normalized_metrics']['capacity'] if org_result['normalized_metrics'] else 0,
                        'annual_revenue': org_result['extracted_data'].get('annual_revenue') or '',
                        'total_expenses': org_result['extracted_data'].get('total_expenses') or '',
                        'population_served': org_result['extracted_data'].get('population_served') or '',
                        'employees': org_result['extracted_data'].get('employees') or '',
                        'data_quality': 'High' if org_result['quality_score'] > 0.7 else 'Medium' if org_result['quality_score'] > 0.3 else 'Low',
                    }
                    writer.writerow(row)
            
            logger.info(f"Enriched data written to: {output_path}")
        
        except Exception as e:
            logger.error(f"Error writing enriched CSV: {e}")

    def _generate_ranking(self, csv_path: str) -> None:
        """Use algov1 to generate ranking."""
        try:
            ranked_output = csv_path.replace('.csv', '_ranked.csv')
            shelters = algov1.process_csv(csv_path)
            algov1.write_ranked_csv(shelters, ranked_output)
            
            logger.info(f"\nRanking generated: {ranked_output}")
            logger.info("Top 10 organizations:")
            for s in shelters[:10]:
                logger.info(f"  {s['rank']:>2}: {s['name']:30} score={s['score']:.3f}")
        
        except Exception as e:
            logger.error(f"Error generating ranking: {e}")


def main():
    """Example usage."""
    # Set up API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("Please set GEMINI_API_KEY environment variable")
        return
    
    # Create collector
    collector = OrganizationDataCollector(api_key)
    
    # Example: process a CSV file with organizations
    input_csv = "organizations.csv"  # Expected format: org_name, website
    
    if os.path.exists(input_csv):
        collector.process_org_list(input_csv, use_cache=True)
    else:
        # Example single organization
        logger.info("No organizations.csv found. Processing single example...")
        
        result = collector.collect_organization_data(
            "Sample Nonprofit",
            "example.org"
        )
        
        logger.info("\nFinal Result:")
        logger.info(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
