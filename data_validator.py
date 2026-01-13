"""
Data validator to ensure extracted metrics are accurate and within expected ranges.
"""

import logging
from typing import Dict, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataValidator:
    """Validate extracted financial and operational data."""
    
    # Define reasonable ranges for nonprofit organizations
    REVENUE_RANGE = (0, 500_000_000)  # 0 to 500M
    EXPENSE_RANGE = (0, 500_000_000)
    POPULATION_RANGE = (0, 1_000_000)
    EMPLOYEE_RANGE = (0, 10_000)
    VOLUNTEER_RANGE = (0, 50_000)
    
    @staticmethod
    def validate_revenue(revenue: float) -> Tuple[bool, str]:
        """Validate revenue value."""
        if revenue is None:
            return True, "No revenue data provided"
        
        if not isinstance(revenue, (int, float)):
            return False, f"Revenue must be numeric, got {type(revenue)}"
        
        if revenue < 0:
            return False, "Revenue cannot be negative"
        
        if revenue > DataValidator.REVENUE_RANGE[1]:
            return False, f"Revenue {revenue:,.0f} exceeds expected range"
        
        return True, "Valid"

    @staticmethod
    def validate_expenses(expenses: float, revenue: float = None) -> Tuple[bool, str]:
        """Validate expenses and check against revenue if provided."""
        if expenses is None:
            return True, "No expense data provided"
        
        if not isinstance(expenses, (int, float)):
            return False, f"Expenses must be numeric, got {type(expenses)}"
        
        if expenses < 0:
            return False, "Expenses cannot be negative"
        
        if expenses > DataValidator.EXPENSE_RANGE[1]:
            return False, f"Expenses {expenses:,.0f} exceeds expected range"
        
        # Check if expenses exceed revenue (common data error)
        if revenue is not None and revenue > 0 and expenses > revenue * 1.1:
            return False, f"Expenses {expenses:,.0f} significantly exceed revenue {revenue:,.0f}"
        
        return True, "Valid"

    @staticmethod
    def validate_population(population: int) -> Tuple[bool, str]:
        """Validate population served."""
        if population is None:
            return True, "No population data provided"
        
        if not isinstance(population, (int, float)):
            return False, f"Population must be numeric, got {type(population)}"
        
        if population < 0:
            return False, "Population cannot be negative"
        
        if population > DataValidator.POPULATION_RANGE[1]:
            return False, f"Population {population:,.0f} exceeds expected range"
        
        return True, "Valid"

    @staticmethod
    def validate_employees(employees: int) -> Tuple[bool, str]:
        """Validate employee count."""
        if employees is None:
            return True, "No employee data provided"
        
        if not isinstance(employees, (int, float)):
            return False, f"Employees must be numeric, got {type(employees)}"
        
        if employees < 0:
            return False, "Employees cannot be negative"
        
        if employees > DataValidator.EMPLOYEE_RANGE[1]:
            return False, f"Employees {employees:,.0f} exceeds expected range"
        
        return True, "Valid"

    @staticmethod
    def validate_volunteers(volunteers: int) -> Tuple[bool, str]:
        """Validate volunteer count."""
        if volunteers is None:
            return True, "No volunteer data provided"
        
        if not isinstance(volunteers, (int, float)):
            return False, f"Volunteers must be numeric, got {type(volunteers)}"
        
        if volunteers < 0:
            return False, "Volunteers cannot be negative"
        
        if volunteers > DataValidator.VOLUNTEER_RANGE[1]:
            return False, f"Volunteers {volunteers:,.0f} exceeds expected range"
        
        return True, "Valid"

    @classmethod
    def validate_all(cls, data: Dict) -> Dict[str, Tuple[bool, str]]:
        """Validate all extracted data fields."""
        results = {}
        
        results['revenue'] = cls.validate_revenue(data.get('annual_revenue'))
        results['expenses'] = cls.validate_expenses(
            data.get('total_expenses'),
            data.get('annual_revenue')
        )
        results['population'] = cls.validate_population(
            data.get('population_served') or data.get('clients_served')
        )
        results['employees'] = cls.validate_employees(
            data.get('full_time_employees') or data.get('employees')
        )
        results['volunteers'] = cls.validate_volunteers(data.get('volunteers'))
        
        return results

    @staticmethod
    def get_data_quality_score(extracted_data: Dict, validation_results: Dict) -> float:
        """
        Calculate overall data quality score (0-1).
        Based on:
        - Number of valid fields
        - Confidence scores from extraction
        - Validation results
        """
        valid_count = sum(1 for _, (is_valid, _) in validation_results.items() if is_valid)
        total_fields = len(validation_results)
        
        base_score = valid_count / total_fields if total_fields > 0 else 0
        
        # Adjust based on confidence scores
        confidence_scores = extracted_data.get('confidence_scores', {})
        if confidence_scores:
            avg_confidence = sum(confidence_scores.values()) / len(confidence_scores) if confidence_scores else 0
            base_score = (base_score + avg_confidence) / 2
        
        return max(0, min(1, base_score))

    @staticmethod
    def log_validation_results(org_name: str, validation_results: Dict) -> None:
        """Log validation results."""
        logger.info(f"\n--- Validation Results for {org_name} ---")
        for field, (is_valid, message) in validation_results.items():
            status = "✓" if is_valid else "✗"
            logger.info(f"  {status} {field}: {message}")

    @staticmethod
    def cross_check_with_irs_990(revenue: float, expenses: float) -> Tuple[bool, str]:
        """
        Cross-check data against typical IRS Form 990 ratios.
        Returns (is_reasonable, message)
        """
        if not revenue or not expenses:
            return True, "Insufficient data for cross-check"
        
        if expenses < 0 or revenue < 0:
            return False, "Negative values detected"
        
        # Typical programs expense ratio for nonprofits: 65-80%
        if revenue > 0:
            program_ratio = 0.75  # Assume 75% is programs
            
            # Check if expenses are in reasonable range
            min_expected = revenue * 0.6
            max_expected = revenue * 1.1
            
            if expenses < min_expected or expenses > max_expected:
                return False, f"Expenses {expenses:,.0f} outside typical range {min_expected:,.0f}-{max_expected:,.0f}"
        
        return True, "Data appears consistent with typical nonprofit financials"


def main():
    # Example usage
    test_data = {
        'annual_revenue': 2_500_000,
        'total_expenses': 2_400_000,
        'population_served': 5_000,
        'employees': 45,
        'volunteers': 120,
        'confidence_scores': {'revenue': 0.9, 'population': 0.85, 'expenses': 0.88}
    }
    
    validator = DataValidator()
    results = validator.validate_all(test_data)
    validator.log_validation_results("Test Org", results)
    
    quality_score = validator.get_data_quality_score(test_data, results)
    print(f"\nData Quality Score: {quality_score:.2%}")
    
    irs_check = validator.cross_check_with_irs_990(
        test_data.get('annual_revenue'),
        test_data.get('total_expenses')
    )
    print(f"IRS Cross-Check: {irs_check}")


if __name__ == "__main__":
    main()
