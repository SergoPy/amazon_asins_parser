def validate_asins_monitoring_request(data: dict) -> bool:
    param_keys = ['seller_name', 'product_name', 'personal_asin', 'competitor_asins',
                  'keywords', 'asins_google_sheet_link', 'frequency']
    values = [data[key] for key in param_keys]
    return all(values)


def validate_advertising_monitoring_requests(data: dict) -> bool:
    param_keys = [
        'account_name_adv', 'asins_adv', 'asins_google_sheet_link_adv', 'password_adv', 'login_adv',
        'entity_id_adv', 'target_acos_adv', 'product_name_adv', 'start_date_adv', 'end_date_adv'
    ]
    values = [data[key] for key in param_keys]
    return all(values)


def term_report_validator_request(files: dict) -> bool:
    required_fields = files.get('file1'), files.get('file2')
    return all(required_fields)


def campaign_upload_validator(data: dict, files: dict):
    values_keys = ['login', 'password', 'upload_campaign_mode', 'creative_asins']
    values = [data[key] for key in values_keys]
    return all(values) and len(files)
