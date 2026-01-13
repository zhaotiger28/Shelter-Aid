"""
Gemini API-based data extraction from documents and websites.
Extracts financial, operational, and impact metrics.
"""

import google.generativeai as genai
import base64
import logging
import json
from typing import Dict, Optional, Any
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiExtractor:
    def __init__(self, api_key: str):
        """Initialize Gemini client with API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def extract_from_text(self, text: str, org_name: str = "") -> Dict[str, Any]:
        """
        Extract financial and operational metrics from text content.
        
        Returns structured data:
        {
            'annual_revenue': float,
            'total_expenses': float,
            'program_expenses': float,
            'administrative_expenses': float,
            'population_served': int,
            'employees': int,
            'volunteers': int,
            'geographic_coverage': str,
            'primary_focus': str,
            'economic_impact': str,
            'confidence_scores': {}
        }
        """
        if not text or len(text.strip()) == 0:
            return self._empty_result()

        prompt = f"""
You are a financial analyst for nonprofit organizations. Extract key financial and operational metrics from this document.

Organization: {org_name}

Document text:
{text[:5000]}

Extract the following data and return as JSON. If a value is not found, set it to null:
{{
    "annual_revenue": <number or null>,
    "total_expenses": <number or null>,
    "program_expenses": <number or null>,
    "administrative_expenses": <number or null>,
    "fundraising_expenses": <number or null>,
    "population_served": <number or null>,
    "clients_served": <number or null>,
    "employees": <number or null>,
    "full_time_employees": <number or null>,
    "part_time_employees": <number or null>,
    "volunteers": <number or null>,
    "geographic_coverage": <string or null>,
    "primary_focus": <string or null>,
    "service_areas": <array of strings or null>,
    "economic_impact": <string description or null>,
    "annual_impact": <string description or null>,
    "key_programs": <array of strings or null>,
    "year": <year integer or null>,
    "confidence_notes": <string with any caveats>
}}

Return ONLY valid JSON, no other text.
"""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Parse response
            response_text = response.text.strip()
            
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            
            # Add confidence scores
            result['confidence_scores'] = {
                'revenue': 0.8 if result.get('annual_revenue') else 0,
                'population': 0.8 if result.get('population_served') or result.get('clients_served') else 0,
                'expenses': 0.7 if result.get('total_expenses') else 0,
            }
            
            logger.info(f"Successfully extracted data for {org_name}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"Error extracting data from text: {e}")
            return self._empty_result()

    def extract_from_pdf(self, pdf_content: bytes, org_name: str = "") -> Dict[str, Any]:
        """
        Extract data from PDF content using Gemini's vision capabilities.
        """
        try:
            # Encode PDF to base64
            pdf_base64 = base64.standard_b64encode(pdf_content).decode('utf-8')
            
            prompt = f"""
You are a financial analyst for nonprofit organizations. Extract key financial and operational metrics from this PDF document.

Organization: {org_name}

Extract the following data and return as JSON:
{{
    "annual_revenue": <number or null>,
    "total_expenses": <number or null>,
    "program_expenses": <number or null>,
    "administrative_expenses": <number or null>,
    "population_served": <number or null>,
    "employees": <number or null>,
    "volunteers": <number or null>,
    "geographic_coverage": <string or null>,
    "primary_focus": <string or null>,
    "economic_impact": <string or null>,
    "year": <year integer or null>,
    "confidence_notes": <string>
}}

Return ONLY valid JSON.
"""
            
            # Use vision capabilities
            response = self.model.generate_content([
                prompt,
                {
                    "mime_type": "application/pdf",
                    "data": pdf_base64
                }
            ])
            
            response_text = response.text.strip()
            
            # Extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(response_text)
            result['confidence_scores'] = {
                'revenue': 0.85 if result.get('annual_revenue') else 0,
                'population': 0.85 if result.get('population_served') else 0,
                'expenses': 0.8 if result.get('total_expenses') else 0,
            }
            
            logger.info(f"Successfully extracted PDF data for {org_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting from PDF: {e}")
            return self._empty_result()

    def extract_from_html(self, html_content: str, org_name: str = "") -> Dict[str, Any]:
        """Extract data from HTML content."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            
            # Use text extraction
            return self.extract_from_text(text, org_name)
        
        except Exception as e:
            logger.error(f"Error extracting from HTML: {e}")
            return self._empty_result()

    def normalize_metrics(self, extracted: Dict[str, Any]) -> Dict[str, float]:
        """
        Normalize extracted metrics to algov1.py format:
        - finance (0-10): Based on revenue and sustainability
        - supply (0-10): Based on funding availability
        - population (0-10): Normalized population served
        - urgency (0-10): Need assessment
        - capacity (0-10): Operational capacity
        """
        
        revenue = extracted.get('annual_revenue') or 0
        expenses = extracted.get('total_expenses') or revenue
        population = extracted.get('population_served') or extracted.get('clients_served') or 0
        employees = extracted.get('full_time_employees') or extracted.get('employees') or 0
        
        # Finance score: revenue sustainability (0-10)
        if revenue > 0:
            # Higher revenue = better finance score
            finance_score = min(10, (revenue / 1000000) * 2)  # Normalize to 10M scale
        else:
            finance_score = 3.0  # Low score if no revenue data
        
        # Supply score: funding efficiency (0-10)
        if expenses > 0 and revenue > 0:
            efficiency = revenue / expenses
            supply_score = min(10, efficiency * 5)
        else:
            supply_score = 5.0
        
        # Population score: scale to 0-10
        if population > 0:
            population_score = min(10, (population / 10000) * 2)  # Normalize to 10K people scale
        else:
            population_score = 3.0
        
        # Capacity score: based on employees (proxy for operational capacity)
        if employees > 0:
            capacity_score = min(10, (employees / 50) * 2)  # Normalize to 50 employees scale
        else:
            capacity_score = 3.0
        
        # Urgency score: needs assessment (default mid-range without specific data)
        urgency_score = 5.0
        
        return {
            'finance': max(0, min(10, finance_score)),
            'supply': max(0, min(10, supply_score)),
            'population': max(0, min(10, population_score)),
            'urgency': max(0, min(10, urgency_score)),
            'capacity': max(0, min(10, capacity_score)),
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure."""
        return {
            'annual_revenue': None,
            'total_expenses': None,
            'program_expenses': None,
            'administrative_expenses': None,
            'population_served': None,
            'employees': None,
            'volunteers': None,
            'geographic_coverage': None,
            'primary_focus': None,
            'economic_impact': None,
            'year': None,
            'confidence_notes': 'No data extracted',
            'confidence_scores': {'revenue': 0, 'population': 0, 'expenses': 0}
        }


def main():
    # Example usage
    import os
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not set")
        return
    
    extractor = GeminiExtractor(api_key)
    
    # Example text
    sample_text = """
    Annual Report 2023
    Our organization served 5,000 clients this year.
    Total revenue: $2,500,000
    Total expenses: $2,400,000
    Program expenses: $2,000,000
    We employed 45 full-time staff members.
    """
    
    result = extractor.extract_from_text(sample_text, "Sample Org")
    print("Extracted data:", json.dumps(result, indent=2))
    
    normalized = extractor.normalize_metrics(result)
    print("Normalized metrics:", normalized)


if __name__ == "__main__":
    main()
