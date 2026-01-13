# Shelter-Aid: Automated Organization Data Collection System

Automated pipeline that scrapes organization websites, finds tax forms and economic reports, extracts metrics using Gemini AI, and generates ranked CSV for shelter funding decisions.

## Features

✅ **Automated Web Scraping** - Finds 990 forms, annual reports, impact reports  
✅ **Gemini AI Extraction** - Intelligently extracts financial and operational metrics  
✅ **Data Validation** - Cross-checks with typical nonprofit ratios  
✅ **Systematic Accuracy** - Multiple validation layers ensure data quality  
✅ **Runtime Processing** - Only needs org name + website URL  
✅ **Caching** - Avoids re-processing same organizations  
✅ **Integration** - Works with existing ranking algorithm  

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Gemini API Key

Get your free API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY = "your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Linux/Mac:**
```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or add to `.env` file and load it:
```
GEMINI_API_KEY=your-api-key-here
```

## Usage

### Option 1: Process CSV File (Recommended)

Create `organizations.csv`:
```csv
org_name,website
Red Cross,redcross.org
Salvation Army,salvationarmy.org
Local Food Bank,localfoodbank.org
```

Run the collection:
```python
from data_orchestrator import OrganizationDataCollector
import os

api_key = os.getenv('GEMINI_API_KEY')
collector = OrganizationDataCollector(api_key)
collector.process_org_list('organizations.csv')
```

This generates:
- `organizations_enriched.csv` - With extracted metrics
- `organizations_enriched_ranked.csv` - Ranked by priority

### Option 2: Process Single Organization

```python
from data_orchestrator import OrganizationDataCollector
import os

api_key = os.getenv('GEMINI_API_KEY')
collector = OrganizationDataCollector(api_key)

result = collector.collect_organization_data(
    org_name="Red Cross",
    website="redcross.org"
)

print(result['normalized_metrics'])
# Output: {
#   'finance': 8.5,
#   'supply': 7.2,
#   'population': 9.1,
#   'urgency': 6.0,
#   'capacity': 8.0
# }
```

### Option 3: Command Line

```bash
# Process CSV (after setting GEMINI_API_KEY)
python data_orchestrator.py
```

## How It Works

### Pipeline Architecture

```
Input: org_name, website
    ↓
[1] Web Scraper
    - Crawls website (max 20 pages)
    - Searches for: 990 forms, annual reports, impact reports
    - Returns URLs of found documents
    ↓
[2] Document Fetcher
    - Downloads PDFs and HTML documents
    - Extracts text (handles corrupted PDFs gracefully)
    ↓
[3] Gemini Extractor
    - Sends document text to Gemini 2.0 Flash
    - Extracts: revenue, expenses, population served, employees, etc.
    - Returns structured JSON
    ↓
[4] Data Validator
    - Validates ranges (e.g., revenue $0-500M)
    - Cross-checks expense/revenue ratios
    - Compares against IRS Form 990 typical patterns
    - Assigns confidence scores
    ↓
[5] Normalizer
    - Converts financial metrics to 0-10 scale
    - Calculates: finance, supply, population, urgency, capacity
    ↓
[6] Ranking Algorithm (algov1.py)
    - Applies weights: finance(0.15), supply(0.25), population(0.1), 
                       urgency(0.3), capacity(0.2)
    - Prioritizes niche organizations
    ↓
Output: Ranked CSV with all metrics
```

## Data Extraction Mapping

**Gemini extracts:**
- Annual revenue
- Total expenses / Program expenses / Admin expenses
- Population served
- Employees (full-time, part-time)
- Volunteers
- Geographic coverage
- Service focus areas
- Economic impact statements

**Normalized to 0-10 scale:**
- `finance` = revenue sustainability (0-10)
- `supply` = funding efficiency (0-10)
- `population` = people served (0-10)
- `urgency` = need assessment (0-10, default 5.0)
- `capacity` = operational capacity (0-10)

## Data Quality & Validation

Each organization gets a **quality score (0-1%)**:

| Score | Status | Details |
|-------|--------|---------|
| 70%+ | High | Multiple valid fields, confident extraction |
| 30-70% | Medium | Some fields found, partial data |
| <30% | Low | Minimal data or high uncertainty |

Validation checks:
✓ Revenue within $0-500M range  
✓ Expenses don't exceed revenue by >10%  
✓ Population served within $0-1M range  
✓ Employee count $0-10K range  
✓ IRS 990 pattern matching  

## Caching

Extracted data is cached in `./extraction_cache/` to avoid re-processing.

To skip cache for fresh data:
```python
result = collector.collect_organization_data(
    org_name="Red Cross",
    website="redcross.org",
    use_cache=False  # Force re-extraction
)
```

## Error Handling

The system handles:
- Broken/expired website links
- Missing documents
- Corrupted PDFs
- Network timeouts
- Invalid data formats
- SSL certificate issues

**Graceful degradation:** Returns partial data rather than failing entirely.

## Performance & Costs

**Speed:** ~2-3 minutes per organization (scraping + extraction)
**API Cost:** ~500-1000 tokens per organization ($0.002-0.004 with Gemini)

**Batch Processing Tips:**
- Process during off-peak hours
- Use `use_cache=True` to skip re-extraction
- Limit to 20-30 orgs per batch on free tier

## Example Output

### enriched.csv
```csv
name,website,finance,supply,population,urgency,capacity,quality_score,status
Red Cross,redcross.org,8.5,7.2,9.1,6.0,8.0,85%,success
Salvation Army,salvationarmy.org,7.8,6.9,8.5,5.0,7.5,79%,success
```

### enriched_ranked.csv
```csv
rank,name,niche,score,finance,supply,population,urgency,capacity
1,Salvation Army,False,0.745,7.8,6.9,8.5,5.0,7.5
2,Red Cross,False,0.732,8.5,7.2,9.1,6.0,8.0
```

## Troubleshooting

**Error: GEMINI_API_KEY not set**
```bash
# Windows PowerShell
$env:GEMINI_API_KEY = "your-key"

# Check it's set
$env:GEMINI_API_KEY
```

**SSL Certificate Errors**
- The scraper ignores SSL warnings for robustness
- If you get persistent errors, check your internet connection

**Empty extractions**
- Website may not have public financial documents
- Try manually checking the website first
- Check `extraction_cache/` to see what was found

**Slow processing**
- Normal: 2-3 min per org
- API rate limiting after ~10 requests/minute
- Use caching to speed up re-runs

## Files

- `data_orchestrator.py` - Main orchestrator (use this)
- `web_scraper.py` - Website crawler
- `gemini_extractor.py` - Gemini-based extraction
- `data_validator.py` - Validation & quality scoring
- `algov1.py` - Original ranking algorithm
- `extraction_cache/` - Cached results
- `organizations.csv` - Input: org name + website

## API Reference

### OrganizationDataCollector

```python
from data_orchestrator import OrganizationDataCollector

collector = OrganizationDataCollector(
    gemini_api_key="your-key",
    cache_dir="./extraction_cache"
)

# Process single org
result = collector.collect_organization_data(
    org_name="Sample Org",
    website="example.org",
    use_cache=True
)

# Process CSV file
collector.process_org_list(
    csv_path="organizations.csv",
    output_path="results.csv",
    use_cache=True
)
```

### Result Structure

```json
{
  "org_name": "Red Cross",
  "website": "redcross.org",
  "status": "success",
  "quality_score": 0.85,
  "normalized_metrics": {
    "finance": 8.5,
    "supply": 7.2,
    "population": 9.1,
    "urgency": 6.0,
    "capacity": 8.0
  },
  "extracted_data": {
    "annual_revenue": 2500000,
    "total_expenses": 2400000,
    "population_served": 50000,
    "employees": 450,
    "volunteers": 2000
  },
  "documents_found": {
    "tax_forms": ["url1", "url2"],
    "annual_reports": ["url3"],
    "impact_reports": [],
    "other_financial": []
  }
}
```

## Future Enhancements

- [ ] Support for GuideStar/Charity Navigator API
- [ ] Multi-language document support
- [ ] Incremental updates tracking
- [ ] Donor database integration
- [ ] Custom extraction templates per org type
- [ ] Web UI for monitoring

## License

MIT

## Support

For issues or questions, check the logs in `extraction_cache/` directory.
