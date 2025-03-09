from typing import Any, Dict
from datetime import datetime
import logging, validators
from monday_types import ValidationResult, ColumnValue
from monday_validators import (normalize_text, validate_date, validate_phone)

logger = logging.getLogger('monday_handlers')

class ColumnTypeHandler:
    """Base class for handling different column types"""
    def format_value(self, value: Any, settings: Dict) -> ColumnValue:
        """Format and validate a value according to column type"""
        validation = self.validate_value(value, settings)
        if validation.is_valid:
            transformed = self.transform_value(validation.transformed_value or value, settings)
            return ColumnValue(raw_value=value, formatted_value=transformed, validation_result=validation)
        return ColumnValue(raw_value=value, formatted_value=None, validation_result=validation)

    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        raise NotImplementedError
        
    def transform_value(self, value: Any, settings: Dict) -> Any:
        raise NotImplementedError

    def get_validation_rules(self, settings: Dict) -> Dict[str, Any]:
        """Get validation rules for the column type"""
        return {
            "type": self.__class__.__name__.replace("Handler", "").lower(),
            "required": settings.get("mandatory", False)
        }

class TextColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            normalized = normalize_text(str(value))
            if not normalized.strip(): 
                return ValidationResult(is_valid=False, message="Text cannot be empty after normalization")
            return ValidationResult(is_valid=True, transformed_value=normalized)
        except Exception as e:
            return ValidationResult(is_valid=False, message=f"Text validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        normalized = normalize_text(str(value))
        return {"text": normalized}

class LongTextColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return ValidationResult(True, "")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"text": str(value)}

class NumberColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            float(value)
            return ValidationResult(True, "")
        except ValueError:
            return ValidationResult(False, f"Invalid number value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        try:
            return {"number": float(value)}
        except ValueError as e:
            logger.error(f"Invalid number value: {value}", exc_info=True)
            raise

class DateColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            return validate_date(str(value), settings)
        except ValueError as e:
            return ValidationResult(False, str(e))

    def transform_value(self, value: Any, settings: Dict) -> Any:
        try:
            date_str = str(value).split('T')[0]
            return {"date": date_str}
        except Exception as e:
            logger.error(f"Date transform error: {str(e)}")
            raise ValueError(f"Invalid date format: {str(e)}")

    def get_validation_rules(self, settings: Dict) -> Dict[str, Any]:
        rules = super().get_validation_rules(settings)
        rules.update({
            "format": "ISO8601",
            "includes_time": settings.get("time", False),
            "timezone": settings.get("timezone", "UTC")
        })
        return rules

class EmailColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if '@' in str(value): return ValidationResult(True, "")
        return ValidationResult(False, f"Invalid email value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"email": str(value), "text": str(value)}

class PhoneColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        country_code = settings.get("country_code")
        return validate_phone(value, country_code)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        validation = validate_phone(value, settings.get("country_code"))
        if not validation.is_valid:
            raise ValueError(f"Invalid phone number: {validation.message}")
        return {"phone": validation.transformed_value, "code": settings.get("country_code", "")}

class CheckboxColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, (bool, int, str)): return ValidationResult(True, "")
        return ValidationResult(False, f"Invalid checkbox value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"checked": bool(value)}

class LinkColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, dict): url = value.get('url', '')
            else: url = str(value)
                
            if not validators.url(url):
                return ValidationResult(is_valid=False, message="Invalid URL format")
            return ValidationResult(is_valid=True, transformed_value=url)
        except Exception as e:
            return ValidationResult(is_valid=False, message=f"URL validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        if isinstance(value, dict):
            return {"url": value.get("url", ""), "text": value.get("text", "")}
        return {"url": str(value), "text": str(value)}

class ItemIDColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            item_id = str(value)
            if not item_id.strip(): return ValidationResult(False, "Item ID cannot be empty")
            return ValidationResult(True, transformed_value=item_id)
        except:
            return ValidationResult(False, "Invalid Item ID format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"id": str(value)}

class AutoNumberColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            number = int(value)
            if number < 0: return ValidationResult(False, "Auto number must be positive")
            return ValidationResult(True, transformed_value=number)
        except ValueError:
            return ValidationResult(False, "Invalid auto number format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"number": int(value)}

class HourColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, str):
                hours, minutes = value.split(':')
                hours, minutes = int(hours), int(minutes)
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    return ValidationResult(False, "Invalid hour/minute values")
                return ValidationResult(True, transformed_value=f"{hours:02d}:{minutes:02d}")
            return ValidationResult(False, "Hour must be in HH:MM format")
        except ValueError:
            return ValidationResult(False, "Invalid hour format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"hour": value}

class WeekColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, dict):
                week = int(value.get('week', 0))
                year = int(value.get('year', datetime.now().year))
                if not (1 <= week <= 53): return ValidationResult(False, "Week must be between 1 and 53")
                if year < 1900: return ValidationResult(False, "Invalid year")
                return ValidationResult(True, transformed_value={"week": week, "year": year})
            return ValidationResult(False, "Week value must be a dictionary")
        except ValueError:
            return ValidationResult(False, "Invalid week/year format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"week": value.get('week'), "year": value.get('year', datetime.now().year)}