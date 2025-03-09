import re, logging, difflib, unicodedata, colorsys, phonenumbers
import validators as web_validators
from typing import Any, Dict, List, Callable
from datetime import datetime, timezone
from monday_types import ValidationResult, FormulaType, TimeTrackingStatus
from email_validator import validate_email as email_validator, EmailNotValidError 
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

logger = logging.getLogger('monday_validators')

def vresult(valid: bool, message: str = None, value: Any = None, suggestions: List = None) -> ValidationResult:
    return ValidationResult(is_valid=valid, message=message, transformed_value=value, suggested_values=suggestions)

def generic_validator(value: Any, validator_func: Callable, error_msg: str = None, 
                     transform_func: Callable = None, **kwargs) -> ValidationResult:
    try:
        if validator_func(value, **kwargs):
            transformed = value if transform_func is None else transform_func(value, **kwargs)
            return vresult(True, "Valid value", transformed)
        return vresult(False, error_msg or f"Invalid value: {value}")
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return vresult(False, error_msg or str(e))

def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize('NFKD', str(value))
    return ' '.join(normalized.encode('ASCII', 'ignore').decode().split())

def validate_date(value: Any, settings: Dict) -> ValidationResult:
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"]
    user_tz = settings.get('timezone', 'UTC')
    
    for fmt in formats:
        try:
            if '%z' in fmt:
                try: date = datetime.strptime(str(value), fmt)
                except: 
                    date = datetime.strptime(str(value).split('+')[0], fmt.split('%z')[0])
                    date = date.replace(tzinfo=ZoneInfo(user_tz))
            else:
                date = datetime.strptime(str(value), fmt).replace(tzinfo=ZoneInfo(user_tz))
            return vresult(True, "Date formatted successfully", date.astimezone(timezone.utc).strftime("%Y-%m-%d"))
        except ValueError: continue
        
    return vresult(False, f"Invalid date format. Use one of: {', '.join(formats)}")

def validate_email(value: Any) -> ValidationResult:
    try:
        return vresult(True, "Email is valid", email_validator(str(value)).normalized)
    except EmailNotValidError as e:
        return vresult(False, str(e))

def validate_phone(value: Any, country_code: str = None) -> ValidationResult:
    try:
        number = str(value).strip()
        if not number: return vresult(False, "Phone number cannot be empty")
        if country_code and not country_code.strip(): return vresult(False, "Invalid country code")
            
        parsed = phonenumbers.parse(number, country_code)
        if phonenumbers.is_valid_number(parsed):
            formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
            return vresult(True, "Phone number is valid", formatted)
        return vresult(False, "Invalid phone number")
    except Exception as e:
        return vresult(False, f"Phone validation error: {str(e)}")

def validate_location(value: Any) -> ValidationResult:
    try:
        geolocator = Nominatim(user_agent="monday_app", timeout=10)
        try: 
            location = geolocator.geocode(str(value))
            if location:
                return vresult(True, "Location found", 
                              {"lat": str(location.latitude), "lng": str(location.longitude), "address": location.address})
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            return vresult(False, f"Geocoding service error: {str(e)}")
        return vresult(False, "Location not found")
    except Exception as e:
        return vresult(False, f"Location validation error: {str(e)}")

def validate_status(value: Any, settings: Dict) -> ValidationResult:
    if "labels" not in settings: return vresult(False, "No labels defined")
    value_str, labels = str(value).lower(), settings["labels"]
    
    for label_id, label_text in labels.items():
        if value_str == str(label_text).lower():
            return vresult(True, "Valid status value")
            
    matches = difflib.get_close_matches(value_str, [str(l).lower() for l in labels.values()], n=3, cutoff=0.6)
    if matches:
        return vresult(False, f"Invalid value. Did you mean one of these? {', '.join(matches)}", suggested_values=matches)
    
    return vresult(False, f"Invalid value. Valid options are: {', '.join(labels.values())}")

def validate_url(value: Any) -> ValidationResult:
    try:
        url = str(value) if str(value).startswith(('http://', 'https://')) else f'https://{value}'
        if not web_validators.url(url): return vresult(False, "Invalid URL format")
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]): return vresult(False, "URL must have scheme and domain")
        return vresult(True, "Valid URL", url)
    except Exception as e:
        return vresult(False, f"URL validation error: {str(e)}")

def validate_composite(value: Any, validator_func: Callable, required_fields: List[str], 
                      field_name: str, settings: Dict = None) -> ValidationResult:
    """Validador genérico para tipos compuestos (dict)"""
    if not isinstance(value, dict):
        return vresult(False, f"{field_name} value must be a dictionary")
    
    for field in required_fields:
        if field not in value or not value[field]:
            return vresult(False, f"{field_name} requires '{field}' field")
    
    try:
        return validator_func(value, settings or {})
    except Exception as e:
        return vresult(False, f"{field_name} validation error: {str(e)}")

VALIDATORS = {
    "formula": lambda v, s: generic_validator(
        v, lambda x, _: bool(str(x).strip()), "Formula cannot be empty",
        lambda x, s: {"formula": str(x), "result_type": s.get('result_type', FormulaType.TEXT)}, settings=s),
        
    "connect_boards": lambda v, s: validate_composite(
        v, 
        lambda x, s: vresult(True, "Valid boards connection", {"board_id": x['board_id'], "item_ids": x['item_ids']}),
        ["board_id"], "Connect boards", s),
        
    "time_tracking": lambda v, s: validate_composite(
        v, 
        lambda x, _: vresult(
            x['status'] in [s.value for s in TimeTrackingStatus] and isinstance(x.get('duration', 0), (int, float)),
            "Valid time tracking", {"status": x['status'], "duration": int(x.get('duration', 0))}
        ), 
        ["status"], "Time tracking"),
        
    "color_picker": lambda v, s: generic_validator(
        v, 
        lambda x, _: isinstance(x, dict) and re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', x.get('color', '')),
        "Invalid color format (use hex)",
        lambda x, _: {
            "color": x.get('color', ''), 
            "label": x.get('label', ''),
            "metadata": {"rgb": tuple(int(x.get('color', '#000')[1:][i:i+2], 16)/255 for i in (0, 2, 4)),
                        "hsv": colorsys.rgb_to_hsv(*tuple(int(x.get('color', '#000')[1:][i:i+2], 16)/255 for i in (0, 2, 4)))}
        }),
        
    "dependency": lambda v, s: validate_composite(
        v,
        lambda x, s: vresult(
            isinstance(x.get('depends_on', []), list) and isinstance(x.get('required_for', []), list) and
            len(x.get('depends_on', [])) + len(x.get('required_for', [])) <= s.get('max_dependencies', 50),
            "Valid dependencies",
            {"depends_on": x.get('depends_on', []), "required_for": x.get('required_for', []), 
             "blocking": bool(x.get('blocking', False))}
        ),
        [], "Dependency", s),
        
    "progress": lambda v, s: generic_validator(
        v,
        lambda x, _: (isinstance(x, dict) and 0 <= float(x.get('progress', 0)) <= 100) or 
                     (isinstance(x, (int, float)) and 0 <= float(x) <= 100),
        "Progress must be between 0 and 100",
        lambda x, _: {"progress": float(x.get('progress', x) if isinstance(x, (int, float)) else x.get('progress', 0)), 
                     "auto_progress": bool(x.get('auto_progress', False)) if isinstance(x, dict) else False})
}

validate_formula = VALIDATORS["formula"]
validate_connect_boards = VALIDATORS["connect_boards"]
validate_time_tracking = VALIDATORS["time_tracking"]
validate_color_picker = VALIDATORS["color_picker"]
validate_dependency = VALIDATORS["dependency"]
validate_progress = VALIDATORS["progress"]