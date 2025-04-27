import json
from typing import Dict, Any
import csv
from datetime import datetime

class TaxSoftwareExport:
    def __init__(self):
        self.proseries_mappings = {
            "W-2": {
                "employee_ssn": "SSN",
                "employer_ein": "EIN",
                "wages_tips_other": "Wages",
                "federal_income_tax": "FederalWithholding",
                "social_security_wages": "SocialSecurityWages",
                "social_security_tax": "SocialSecurityWithheld",
                "medicare_wages": "MedicareWages",
                "medicare_tax": "MedicareWithheld",
                "social_security_tips": "SocialSecurityTips",
                "allocated_tips": "AllocatedTips",
                "dependent_care_benefits": "DependentCareBenefits",
                "nonqualified_plans": "NonqualifiedPlans",
                "statutory_employee": "StatutoryEmployee",
                "retirement_plan": "RetirementPlan",
                "third_party_sick_pay": "ThirdPartySickPay",
                "state": "State",
                "state_id": "StateID",
                "state_wages": "StateWages",
                "state_income_tax": "StateWithholding",
                "local_wages": "LocalWages",
                "local_income_tax": "LocalWithholding",
                "locality_name": "LocalityName"
            },
            "1099-NEC": {
                "payer_name": "PayerName",
                "payer_address": "PayerAddress",
                "payer_tin": "PayerTIN",
                "recipient_name": "RecipientName",
                "recipient_address": "RecipientAddress",
                "recipient_tin": "RecipientTIN",
                "nonemployee_compensation": "NonemployeeCompensation",
                "federal_income_tax": "FederalWithholding",
                "state": "State",
                "state_income": "StateIncome",
                "state_tax_withheld": "StateWithholding",
                "local_income": "LocalIncome",
                "local_tax_withheld": "LocalWithholding"
            }
        }
        
        self.lacerte_mappings = {
            "W-2": {
                "employee_ssn": "SSN",
                "employer_ein": "EIN",
                "wages_tips_other": "Wages",
                "federal_income_tax": "FederalWithholding",
                "social_security_wages": "SocialSecurityWages",
                "social_security_tax": "SocialSecurityWithheld",
                "medicare_wages": "MedicareWages",
                "medicare_tax": "MedicareWithheld",
                "social_security_tips": "SocialSecurityTips",
                "allocated_tips": "AllocatedTips",
                "dependent_care_benefits": "DependentCareBenefits",
                "nonqualified_plans": "NonqualifiedPlans",
                "statutory_employee": "StatutoryEmployee",
                "retirement_plan": "RetirementPlan",
                "third_party_sick_pay": "ThirdPartySickPay",
                "state": "State",
                "state_id": "StateID",
                "state_wages": "StateWages",
                "state_income_tax": "StateWithholding",
                "local_wages": "LocalWages",
                "local_income_tax": "LocalWithholding",
                "locality_name": "LocalityName"
            },
            "1099-NEC": {
                "payer_name": "PayerName",
                "payer_address": "PayerAddress",
                "payer_tin": "PayerTIN",
                "recipient_name": "RecipientName",
                "recipient_address": "RecipientAddress",
                "recipient_tin": "RecipientTIN",
                "nonemployee_compensation": "NonemployeeCompensation",
                "federal_income_tax": "FederalWithholding",
                "state": "State",
                "state_income": "StateIncome",
                "state_tax_withheld": "StateWithholding",
                "local_income": "LocalIncome",
                "local_tax_withheld": "LocalWithholding"
            }
        }
    
    def export_to_proseries(self, data: Dict[str, Any], form_type: str, output_path: str):
        """Export data to ProSeries format."""
        if form_type not in self.proseries_mappings:
            raise ValueError(f"Unsupported form type for ProSeries: {form_type}")
        
        # Map the data to ProSeries format
        mapped_data = {}
        for key, value in data.items():
            if key in self.proseries_mappings[form_type]:
                mapped_data[self.proseries_mappings[form_type][key]] = value
        
        # Create CSV file
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=mapped_data.keys())
            writer.writeheader()
            writer.writerow(mapped_data)
        
        return output_path
    
    def export_to_lacerte(self, data: Dict[str, Any], form_type: str, output_path: str):
        """Export data to Lacerte format."""
        if form_type not in self.lacerte_mappings:
            raise ValueError(f"Unsupported form type for Lacerte: {form_type}")
        
        # Map the data to Lacerte format
        mapped_data = {}
        for key, value in data.items():
            if key in self.lacerte_mappings[form_type]:
                mapped_data[self.lacerte_mappings[form_type][key]] = value
        
        # Create CSV file
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=mapped_data.keys())
            writer.writeheader()
            writer.writerow(mapped_data)
        
        return output_path
    
    def export_to_json(self, data: Dict[str, Any], output_path: str):
        """Export data to JSON format."""
        with open(output_path, 'w') as jsonfile:
            json.dump(data, jsonfile, indent=2)
        
        return output_path

# Initialize export handler
tax_export = TaxSoftwareExport() 