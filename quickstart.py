#!/usr/bin/env python3
"""
Quick start script for automated organization data collection.
Run this to get started immediately.
"""

import os
import sys
import csv
from pathlib import Path

def check_api_key():
    """Check if Gemini API key is set."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set!")
        print("\nTo get started:")
        print("1. Visit: https://makersuite.google.com/app/apikey")
        print("2. Create an API key")
        print("3. Set environment variable:")
        print("   Windows PowerShell: $env:GEMINI_API_KEY = 'your-key-here'")
        print("   Windows CMD: set GEMINI_API_KEY=your-key-here")
        print("   Linux/Mac: export GEMINI_API_KEY='your-key-here'")
        print("\nThen run this script again.")
        sys.exit(1)
    return api_key


def create_sample_csv():
    """Create sample organizations.csv if it doesn't exist."""
    csv_path = Path("organizations.csv")
    
    if csv_path.exists():
        print(f"✓ Found existing {csv_path}")
        return str(csv_path)
    
    print("\nCreating sample organizations.csv...")
    
    sample_orgs = [
        {"org_name": "Red Cross", "website": "redcross.org"},
        {"org_name": "Salvation Army", "website": "salvationarmy.org"},
        {"org_name": "Feeding America", "website": "feedingamerica.org"},
        {"org_name": "Local Food Bank", "website": "example-food-bank.org"},
    ]
    
    try:
        with open(csv_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['org_name', 'website'])
            writer.writeheader()
            writer.writerows(sample_orgs)
        print(f"✓ Created {csv_path} with sample organizations")
        print("  Edit this file to add your actual organizations")
        return str(csv_path)
    except Exception as e:
        print(f"❌ Error creating CSV: {e}")
        sys.exit(1)


def run_collection(api_key: str, csv_path: str):
    """Run the data collection pipeline."""
    try:
        from data_orchestrator import OrganizationDataCollector
        
        print("\n" + "="*60)
        print("Starting Organization Data Collection")
        print("="*60)
        
        collector = OrganizationDataCollector(api_key)
        output_csv = collector.process_org_list(csv_path, use_cache=True)
        
        if output_csv:
            print("\n" + "="*60)
            print("✓ Collection Complete!")
            print("="*60)
            print(f"\nGenerated files:")
            print(f"  • {output_csv.replace('_enriched', '')}")
            print(f"  • {output_csv}")
            print(f"  • {output_csv.replace('.csv', '_ranked.csv')}")
            print("\nOpen the _ranked.csv file to see prioritized organizations.")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("\nMake sure you've installed requirements:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during collection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main():
    """Main entry point."""
    print("🚀 Shelter-Aid Automated Data Collection")
    print("="*60)
    
    # Check API key
    print("\n1️⃣  Checking Gemini API key...")
    api_key = check_api_key()
    print("✓ API key found")
    
    # Check/create CSV
    print("\n2️⃣  Preparing organization list...")
    csv_path = create_sample_csv()
    
    # Show file contents
    print("\nOrganizations to process:")
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            print(f"  {i}. {row['org_name']} ({row['website']})")
    
    # Ask to proceed
    print("\n3️⃣  Ready to collect data?")
    response = input("Proceed? (y/n) ").strip().lower()
    
    if response != 'y':
        print("Cancelled.")
        sys.exit(0)
    
    # Run collection
    print("\n4️⃣  Running collection pipeline...")
    run_collection(api_key, csv_path)


if __name__ == "__main__":
    main()
