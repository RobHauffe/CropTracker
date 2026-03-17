from datetime import date, timedelta

def calculate_predicted_dates(cultivation):
    template = cultivation.template
    if cultivation.sow_date and template:
        if template.expected_days_to_germination is not None:
            cultivation.predicted_germination_date = cultivation.sow_date + timedelta(days=template.expected_days_to_germination)
        
        if template.sow_location == 'Indoors' and template.expected_days_to_transplant is not None:
            cultivation.predicted_transplant_date = cultivation.sow_date + timedelta(days=template.expected_days_to_transplant)
        
        if template.expected_days_to_first_harvest is not None:
            cultivation.predicted_first_harvest_date = cultivation.sow_date + timedelta(days=template.expected_days_to_first_harvest)
        
        if template.expected_days_to_last_harvest is not None:
            cultivation.predicted_last_harvest_date = cultivation.sow_date + timedelta(days=template.expected_days_to_last_harvest)
    return cultivation
