from typing import Any, Dict, Optional, List, Union, Tuple
from datetime import datetime, timezone
import re
import logging
import difflib
import unicodedata
from monday_types import ValidationResult, FormulaType, TimeTrackingStatus
from email_validator import validate_email as email_validator, EmailNotValidError
import phonenumbers
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from zoneinfo import ZoneInfo
import validators
from urllib.parse import urlparse
import json
import colorsys

logger = logging.getLogger('monday_validators')

def validate_date(value: Any, settings: Dict) -> ValidationResult:
    """Validate and transform date values with timezone support"""
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y", 
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z"
    ]
    
    original = str(value)
    user_timezone = settings.get('timezone', 'UTC')
    
    for fmt in formats:
        try:
            if '%z' in fmt:
                try:
                    date = datetime.strptime(original, fmt)
                except ValueError:
                    date = datetime.strptime(original.split('+')[0], fmt.split('%z')[0])
                    date = date.replace(tzinfo=ZoneInfo(user_timezone))
            else:
                date = datetime.strptime(original, fmt)
                date = date.replace(tzinfo=ZoneInfo(user_timezone))
            
            utc_date = date.astimezone(timezone.utc)
            
            return ValidationResult(
                is_valid=True,
                transformed_value=utc_date.strftime("%Y-%m-%d"),
                message="Date formatted successfully"
            )
        except ValueError:
            continue
    
    return ValidationResult(
        is_valid=False,
        message=f"Date must be in one of these formats: {', '.join(formats)}",
        transformed_value=None
    )

def validate_email(value: Any) -> ValidationResult:
    """Validate email format"""
    try:
        email = str(value)
        validated = email_validator(email)
        return ValidationResult(
            is_valid=True,
            transformed_value=validated.normalized,
            message="Email is valid"
        )
    except EmailNotValidError as e:
        return ValidationResult(
            is_valid=False,
            message=str(e)
        )

def validate_phone(value: Any, country_code: str = None) -> ValidationResult:
    """Validate phone numbers with improved error handling"""
    try:
        number = str(value)
        if not number.strip():
            return ValidationResult(
                is_valid=False,
                message="Phone number cannot be empty"
            )
            
        if country_code and not country_code.strip():
            return ValidationResult(
                is_valid=False,
                message="Invalid country code"
            )
            
        parsed = phonenumbers.parse(number, country_code)
        if phonenumbers.is_valid_number(parsed):
            formatted = phonenumbers.format_number(
                parsed, 
                phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            return ValidationResult(
                is_valid=True,
                transformed_value=formatted,
                message="Phone number is valid"
            )
        return ValidationResult(
            is_valid=False,
            message="Invalid phone number"
        )
    except phonenumbers.NumberParseException:
        return ValidationResult(
            is_valid=False,
            message="Could not parse phone number. Please check format and country code."
        )
    except Exception as e:
        logger.error(f"Phone validation error: {str(e)}", exc_info=True)
        return ValidationResult(
            is_valid=False,
            message="Internal validation error"
        )

def validate_location(value: Any) -> ValidationResult:
    """Validate and geocode location"""
    try:
        address = str(value)
        geolocator = Nominatim(user_agent="monday_app", timeout=10)
        
        try:
            location = geolocator.geocode(address)
        except GeocoderTimedOut:
            return ValidationResult(
                is_valid=False,
                message="Geocoding service timeout. Please try again."
            )
        except GeocoderServiceError as e:
            return ValidationResult(
                is_valid=False,
                message=f"Geocoding service error: {str(e)}"
            )
        
        if location:
            return ValidationResult(
                is_valid=True,
                transformed_value={
                    "lat": str(location.latitude),
                    "lng": str(location.longitude),
                    "address": location.address
                },
                message="Location found"
            )
        return ValidationResult(
            is_valid=False,
            message="Location not found. Please check the address."
        )
    except Exception as e:
        logger.error(f"Location validation error: {str(e)}", exc_info=True)
        return ValidationResult(
            is_valid=False,
            message="Error validating location"
        )

def validate_status(value: Any, settings: Dict) -> ValidationResult:
    """Validate status values according to Monday.com specs"""
    logger.debug(f"Validating status value: {value}")
    logger.debug(f"Status settings: {json.dumps(settings, indent=2)}")

    if "labels" not in settings:
        logger.error("No labels defined in settings")
        return ValidationResult(False, "No labels defined")
        
    labels = settings["labels"]
    logger.debug(f"Available labels: {json.dumps(labels, indent=2)}")
    
    value_str = str(value).lower()
    
    for label_id, label_text in labels.items():
        if value_str == str(label_text).lower():
            logger.info(f"Found exact match for '{value}': {label_id}")
            return ValidationResult(True, "Valid status value")
            
    matches = difflib.get_close_matches(
        value_str, 
        [str(l).lower() for l in labels.values()], 
        n=3, 
        cutoff=0.6
    )
    
    if matches:
        logger.info(f"Found similar values for '{value}': {matches}")
        return ValidationResult(
            is_valid=False,
            message=f"Invalid value. Did you mean one of these? {', '.join(matches)}",
            suggested_values=matches
        )
    
    logger.warning(f"No matches found for status value '{value}'")
    return ValidationResult(
        False, 
        f"Invalid value. Valid options are: {', '.join(labels.values())}"
    )

def normalize_text(value: str) -> str:
    """Normalize text removing extra spaces and special characters"""
    normalized = unicodedata.normalize('NFKD', str(value))
    ascii_text = normalized.encode('ASCII', 'ignore').decode()
    return ' '.join(ascii_text.split())

def validate_url(value: Any) -> ValidationResult:
    """Validate URL format and accessibility"""
    try:
        url = str(value)
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        if not validators.url(url):
            return ValidationResult(
                is_valid=False,
                message="Invalid URL format"
            )
            
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return ValidationResult(
                is_valid=False,
                message="URL must contain scheme and domain"
            )
            
        return ValidationResult(
            is_valid=True,
            transformed_value=url,
            message="Valid URL"
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"URL validation error: {str(e)}"
        )

def validate_formula(value: Any, settings: Dict) -> ValidationResult:
    """Validate formula syntax and result type"""
    try:
        formula = str(value)
        result_type = settings.get('result_type', FormulaType.TEXT)
        
        if not formula.strip():
            return ValidationResult(
                is_valid=False, 
                message="Formula cannot be empty"
            )
            
        allowed_functions = settings.get('allowed_functions', [])
        for func in allowed_functions:
            if func not in formula:
                continue
                
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\(.*\)$', func):
                return ValidationResult(
                    is_valid=False,
                    message=f"Invalid function syntax: {func}"
                )
                
        return ValidationResult(
            is_valid=True,
            transformed_value={
                "formula": formula,
                "result_type": result_type
            }
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Formula validation error: {str(e)}"
        )

def validate_connect_boards(value: Any, settings: Dict) -> ValidationResult:
    """Validate board connections"""
    try:
        if isinstance(value, dict):
            board_id = value.get('board_id')
            item_ids = value.get('item_ids', [])
        else:
            return ValidationResult(
                is_valid=False,
                message="Value must be a dictionary with board_id and item_ids"
            )
            
        if not board_id:
            return ValidationResult(
                is_valid=False,
                message="board_id is required"
            )
            
        if not isinstance(item_ids, list):
            return ValidationResult(
                is_valid=False,
                message="item_ids must be a list"
            )
            
        allowed_boards = settings.get('allowed_boards', [])
        if allowed_boards and board_id not in allowed_boards:
            return ValidationResult(
                is_valid=False,
                message=f"Board {board_id} not allowed. Valid boards: {', '.join(allowed_boards)}"
            )
            
        return ValidationResult(
            is_valid=True,
            transformed_value={
                "board_id": board_id,
                "item_ids": item_ids
            }
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Connect boards validation error: {str(e)}"
        )

def validate_time_tracking(value: Any) -> ValidationResult:
    """Validate time tracking data"""
    try:
        if isinstance(value, dict):
            status = value.get('status')
            duration = value.get('duration', 0)
        else:
            return ValidationResult(
                is_valid=False,
                message="Value must be a dictionary with status and duration"
            )
            
        if not status or status not in [s.value for s in TimeTrackingStatus]:
            return ValidationResult(
                is_valid=False,
                message=f"Invalid status. Valid values: {', '.join(s.value for s in TimeTrackingStatus)}"
            )
            
        if not isinstance(duration, (int, float)) or duration < 0:
            return ValidationResult(
                is_valid=False,
                message="Duration must be a non-negative number"
            )
            
        return ValidationResult(
            is_valid=True,
            transformed_value={
                "status": status,
                "duration": int(duration)
            }
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Time tracking validation error: {str(e)}"
        )

def validate_color_picker(value: Any) -> ValidationResult:
    """Validate color values"""
    try:
        if isinstance(value, dict):
            color = value.get('color', '')
            label = value.get('label', '')
        else:
            color = str(value)
            label = ""
            
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            return ValidationResult(
                is_valid=False,
                message="Invalid color format. Must be hex code (e.g. #FF0000)"
            )
            
        try:
            rgb = tuple(int(color.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4))
            hsv = colorsys.rgb_to_hsv(*rgb)
            
            return ValidationResult(
                is_valid=True,
                transformed_value={
                    "color": color,
                    "label": label,
                    "metadata": {
                        "rgb": rgb,
                        "hsv": hsv
                    }
                }
            )
        except Exception:
            return ValidationResult(
                is_valid=False,
                message="Error converting color format"
            )
            
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Color validation error: {str(e)}"
        )

def validate_dependency(value: Any, settings: Dict) -> ValidationResult:
    """Validate item dependencies"""
    try:
        if isinstance(value, dict):
            depends_on = value.get('depends_on', [])
            required_for = value.get('required_for', [])
            blocking = value.get('blocking', False)
        else:
            return ValidationResult(
                is_valid=False,
                message="Value must be a dictionary with depends_on and required_for lists"
            )
            
        if not isinstance(depends_on, list) or not isinstance(required_for, list):
            return ValidationResult(
                is_valid=False,
                message="depends_on and required_for must be lists"
            )
            
        max_dependencies = settings.get('max_dependencies', 50)
        if len(depends_on) + len(required_for) > max_dependencies:
            return ValidationResult(
                is_valid=False,
                message=f"Total dependencies cannot exceed {max_dependencies}"
            )
            
        return ValidationResult(
            is_valid=True,
            transformed_value={
                "depends_on": depends_on,
                "required_for": required_for,
                "blocking": bool(blocking)
            }
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Dependency validation error: {str(e)}"
        )

def validate_progress(value: Any) -> ValidationResult:
    """Validate progress percentage"""
    try:
        if isinstance(value, dict):
            progress = value.get('progress', 0)
            auto_progress = value.get('auto_progress', False)
        else:
            try:
                progress = float(value)
                auto_progress = False
            except ValueError:
                return ValidationResult(
                    is_valid=False,
                    message="Progress must be a number between 0 and 100"
                )
                
        if not isinstance(progress, (int, float)) or not 0 <= progress <= 100:
            return ValidationResult(
                is_valid=False,
                message="Progress must be between 0 and 100"
            )
            
        return ValidationResult(
            is_valid=True,
            transformed_value={
                "progress": float(progress),
                "auto_progress": bool(auto_progress)
            }
        )
    except Exception as e:
        return ValidationResult(
            is_valid=False,
            message=f"Progress validation error: {str(e)}"
        )