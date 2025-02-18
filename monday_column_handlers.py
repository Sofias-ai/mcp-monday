from typing import Any, Dict, Optional
from datetime import datetime
import json
import difflib
from monday_types import (ValidationResult, ColumnValue, FormulaValue, FormulaType, 
                         TimeTrackingStatus, MirrorValue, MirrorType, ButtonValue,
                         CreationLogValue, LastUpdatedValue, DependencyValue,
                         ProgressValue, VoteValue, ColorPickerValue, ConnectBoardsValue)
from monday_validators import (
    validate_date, validate_email, validate_phone, validate_location,
    normalize_text, validate_url, validate_formula, validate_connect_boards,
    validate_time_tracking, validate_color_picker, validate_dependency,
    validate_progress
)
import logging
import validators

logger = logging.getLogger('monday_handlers')

class ColumnTypeHandler:
    """Base class for handling different column types"""
    def format_value(self, value: Any, settings: Dict) -> ColumnValue:
        """Format and validate a value according to column type"""
        validation = self.validate_value(value, settings)
        if validation.is_valid:
            transformed = self.transform_value(
                validation.transformed_value or value, 
                settings
            )
            return ColumnValue(
                raw_value=value,
                formatted_value=transformed,
                validation_result=validation
            )
        return ColumnValue(
            raw_value=value,
            formatted_value=None,
            validation_result=validation
        )

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

class StatusColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        """Validate status value against allowed labels"""
        logger.debug(f"Validating status value: '{value}'")
        logger.debug(f"Status settings: {json.dumps(settings, indent=2)}")
        
        if "labels" not in settings:
            logger.error("No labels defined in settings")
            return ValidationResult(False, "No labels defined for status column")
            
        value_str = str(value)
        settings_labels = settings.get("labels", {})
        
        logger.debug(f"Looking for value '{value_str}' in labels: {json.dumps(settings_labels, indent=2)}")
        
        # Búsqueda exacta case-insensitive
        for label_id, label_text in settings_labels.items():
            if value_str.lower() == str(label_text).lower():
                logger.info(f"Found exact match: ID={label_id}, Text={label_text}")
                return ValidationResult(
                    is_valid=True,
                    transformed_value={"label_id": label_id, "text": label_text},
                    message="Valid status value"
                )
                
        # Si no hay coincidencia exacta, buscar similares
        valid_values = list(settings_labels.values())
        logger.debug(f"No exact match found, searching similar values among: {valid_values}")
        matches = difflib.get_close_matches(value_str, valid_values, n=3, cutoff=0.6)
        
        if matches:
            logger.info(f"Found similar values: {matches}")
            return ValidationResult(
                is_valid=False,
                message=f"Invalid value. Did you mean one of these? {', '.join(matches)}",
                suggested_values=matches
            )
            
        logger.warning(f"No matches found for '{value_str}'")
        return ValidationResult(
            is_valid=False,
            message=f"Invalid value. Valid options are: {', '.join(valid_values)}"
        )

    def format_value(self, value: Any, settings: Dict) -> ColumnValue:
        """Format status value according to Monday.com API specs"""
        logger.debug(f"Formatting status value: '{value}'")
        logger.debug(f"Settings: {json.dumps(settings, indent=2)}")

        validation = self.validate_value(value, settings)
        logger.debug(f"Validation result: {validation}")

        if validation.is_valid and isinstance(validation.transformed_value, dict):
            info = validation.transformed_value
            formatted = {"index": info["label_id"]}
            logger.debug(f"Formatted status value: {formatted}")
            return ColumnValue(
                raw_value=value,
                formatted_value=formatted,
                validation_result=validation
            )
                
        logger.warning(f"Invalid status value: {value}")
        return ColumnValue(
            raw_value=value,
            formatted_value=None,
            validation_result=validation
        )

    def get_validation_rules(self, settings: Dict) -> Dict[str, Any]:
        rules = super().get_validation_rules(settings)
        rules.update({
            "allowed_values": list(settings.get("labels", {}).values())
        })
        return rules

    def transform_value(self, value: Any, settings: Dict) -> Any:
        """Transform status according to Monday.com API specs"""
        if "labels" not in settings:
            raise ValueError("No labels defined in settings")
            
        value_str = str(value).lower()
        for index, label in settings["labels"].items():
            if str(label).lower() == value_str:
                return {"index": str(index)}
                
        raise ValueError(f"Invalid status value: {value}")

class TextColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            normalized = normalize_text(str(value))
            if not normalized.strip():
                return ValidationResult(
                    is_valid=False,
                    message="Text cannot be empty after normalization"
                )
            return ValidationResult(
                is_valid=True,
                transformed_value=normalized
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                message=f"Text validation error: {str(e)}"
            )

    def transform_value(self, value: Any, settings: Dict) -> Any:
        """Transform text according to Monday.com API specs"""
        logger.debug(f"Transforming text value: {value}")
        normalized = normalize_text(str(value))
        formatted = {"text": normalized}
        logger.debug(f"Formatted text value: {formatted}")
        return formatted

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
        """Transform number according to Monday.com API specs"""
        logger.debug(f"Transforming number value: {value}")
        try:
            num_value = float(value)
            formatted = {"number": num_value}
            logger.debug(f"Formatted number value: {formatted}")
            return formatted
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
        """Transform date according to Monday.com API specs"""
        try:
            # Asegurar formato YYYY-MM-DD
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

    def format_value(self, value: Any, settings: Dict) -> ColumnValue:
        """Format date value according to Monday.com API specs"""
        validation = self.validate_value(value, settings)
        if validation.is_valid:
            formatted = {"date": str(value)}  # Simplificado
            return ColumnValue(
                raw_value=value,
                formatted_value=formatted,
                validation_result=validation
            )
        return ColumnValue(
            raw_value=value,
            formatted_value=None,
            validation_result=validation
        )

class EmailColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if '@' in str(value):
            return ValidationResult(True, "")
        return ValidationResult(False, f"Invalid email value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"email": str(value), "text": str(value)}

class LocationColumnHandler(ColumnTypeHandler):
    _location_cache = {}
    
    def _get_cached_location(self, address: str) -> Optional[Dict]:
        """Get location from cache if available"""
        return self._location_cache.get(address)

    def _cache_location(self, address: str, location_data: Dict):
        """Cache location data"""
        self._location_cache[address] = location_data
        if len(self._location_cache) > 1000:
            items_to_remove = int(len(self._location_cache) * 0.1)
            for _ in range(items_to_remove):
                self._location_cache.popitem(last=False)

    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        """Validate location value"""
        try:
            address = str(value)
            
            # Check cache first
            cached = self._get_cached_location(address)
            if cached:
                return ValidationResult(
                    is_valid=True,
                    transformed_value=cached,
                    message="Location found (cached)"
                )
            
            # If not in cache, validate
            result = validate_location(value)
            if result.is_valid:
                self._cache_location(address, result.transformed_value)
            return result
            
        except Exception as e:
            return ValidationResult(False, f"Location validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        """Transform location value"""
        if isinstance(value, dict) and all(k in value for k in ['lat', 'lng', 'address']):
            return value
            
        address = str(value)
        cached = self._get_cached_location(address)
        if cached:
            return cached
            
        result = validate_location(value)
        if not result.is_valid:
            # Si la validación falla, intentamos un formato más simple
            return {
                "lat": "",
                "lng": "",
                "address": address
            }
            
        self._cache_location(address, result.transformed_value)
        return result.transformed_value

class CheckboxColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, (bool, int, str)):
            return ValidationResult(True, "")
        return ValidationResult(False, f"Invalid checkbox value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"checked": bool(value)}

class DropdownColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if "labels" not in settings:
            return ValidationResult(False, "No labels defined for dropdown")
            
        labels = settings["labels"].values()
        value_str = str(value)
        if value_str in labels:
            return ValidationResult(True, "Valid value")
            
        # Fuzzy matching para sugerencias
        matches = difflib.get_close_matches(value_str, labels, n=3, cutoff=0.6)
        if matches:
            return ValidationResult(
                is_valid=False,
                message=f"Invalid value. Did you mean one of these? {', '.join(matches)}",
                suggested_values=matches
            )
        return ValidationResult(
            is_valid=False,
            message=f"Invalid value. Valid options are: {', '.join(labels)}"
        )

    def transform_value(self, value: Any, settings: Dict) -> Any:
        if "labels" in settings and str(value) in settings["labels"]:
            return {"ids": [str(value)]}
        raise ValueError(f"Invalid dropdown value: {value}")

class TagsColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return ValidationResult(True, "")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        tags = value if isinstance(value, list) else [str(value)]
        return {"tag_ids": tags}

class LinkColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, dict):
                url = value.get('url', '')
            else:
                url = str(value)
                
            if not validators.url(url):
                return ValidationResult(
                    is_valid=False,
                    message="Invalid URL format"
                )
            return ValidationResult(
                is_valid=True,
                transformed_value=url
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                message=f"URL validation error: {str(e)}"
            )

    def transform_value(self, value: Any, settings: Dict) -> Any:
        if isinstance(value, dict):
            return {"url": value.get("url", ""), "text": value.get("text", "")}
        return {"url": str(value), "text": str(value)}

class WorldClockColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return ValidationResult(True, "")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"timezone": str(value)}

class CountryColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return ValidationResult(True, "")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"country_code": str(value)}

class PhoneColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        country_code = settings.get("country_code")
        return validate_phone(value, country_code)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        validation = validate_phone(value, settings.get("country_code"))
        if not validation.is_valid:
            raise ValueError(f"Invalid phone number: {validation.message}")
        return {
            "phone": validation.transformed_value,
            "code": settings.get("country_code", "")
        }

class RatingColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            rating = int(float(value))
            max_rating = settings.get("max_rating", 5)
            if 0 <= rating <= max_rating:
                return ValidationResult(True, "")
            return ValidationResult(False, f"Rating must be between 0 and {max_rating}")
        except ValueError:
            return ValidationResult(False, f"Invalid rating value: {value}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        rating = int(float(value))
        max_rating = settings.get("max_rating", 5)
        if not 0 <= rating <= max_rating:
            raise ValueError(f"Rating must be between 0 and {max_rating}")
        return {"rating": rating}

class FileColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return ValidationResult(True, "")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        if isinstance(value, list):
            return {"files": value}
        return {"files": [str(value)]}

class FormulaColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_formula(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        formula_result = validate_formula(value, settings)
        if not formula_result.is_valid:
            raise ValueError(formula_result.message)
        return formula_result.transformed_value

class ConnectBoardsColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_connect_boards(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        connection_result = validate_connect_boards(value, settings)
        if not connection_result.is_valid:
            raise ValueError(connection_result.message)
        return connection_result.transformed_value

class TimeTrackingColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_time_tracking(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        tracking_result = validate_time_tracking(value)
        if not tracking_result.is_valid:
            raise ValueError(tracking_result.message)
        return tracking_result.transformed_value

class ColorPickerColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_color_picker(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        color_result = validate_color_picker(value)
        if not color_result.is_valid:
            raise ValueError(color_result.message)
        return color_result.transformed_value

class DependencyColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_dependency(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        dependency_result = validate_dependency(value, settings)
        if not dependency_result.is_valid:
            raise ValueError(dependency_result.message)
        return dependency_result.transformed_value

class ProgressColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_progress(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        progress_result = validate_progress(value)
        if not progress_result.is_valid:
            raise ValueError(progress_result.message)
        return progress_result.transformed_value

class ButtonColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('label'):
                return ValidationResult(False, "Button must have a label")
            if not value.get('action_id'):
                return ValidationResult(False, "Button must have an action_id")
            return ValidationResult(True, transformed_value=value)
        return ValidationResult(False, "Button value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "label": value.get('label'),
            "action_id": value.get('action_id'),
            "target_type": value.get('target_type'),
            "target_id": value.get('target_id')
        }

class CreationLogColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('created_by') or not value.get('created_at'):
                return ValidationResult(False, "Creation log must have created_by and created_at")
            try:
                datetime.fromisoformat(value['created_at'].replace('Z', '+00:00'))
                return ValidationResult(True, transformed_value=value)
            except ValueError:
                return ValidationResult(False, "Invalid created_at date format")
        return ValidationResult(False, "Creation log value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "created_by": value['created_by'],
            "created_at": value['created_at'],
            "account_id": value.get('account_id')
        }

class LastUpdatedColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('updated_by') or not value.get('updated_at'):
                return ValidationResult(False, "Last updated must have updated_by and updated_at")
            try:
                datetime.fromisoformat(value['updated_at'].replace('Z', '+00:00'))
                return ValidationResult(True, transformed_value=value)
            except ValueError:
                return ValidationResult(False, "Invalid updated_at date format")
        return ValidationResult(False, "Last updated value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "updated_by": value['updated_by'],
            "updated_at": value['updated_at'],
            "account_id": value.get('account_id')
        }

class MirrorColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('source_board_id'):
                return ValidationResult(False, "Mirror must have a source_board_id")
            if value.get('mirror_type') not in [t.value for t in MirrorType]:
                return ValidationResult(False, f"Invalid mirror_type. Valid types: {[t.value for t in MirrorType]}")
            return ValidationResult(True, transformed_value=value)
        return ValidationResult(False, "Mirror value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "source_board_id": value['source_board_id'],
            "mirror_type": value['mirror_type'],
            "filters": value.get('filters', {})
        }

class VoteColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, dict):
                votes_count = int(value.get('votes_count', 0))
                voters = value.get('voters', [])
                if not isinstance(voters, list):
                    return ValidationResult(False, "Voters must be a list")
                return ValidationResult(True, transformed_value={"votes_count": votes_count, "voters": voters})
            return ValidationResult(False, "Vote value must be a dictionary")
        except ValueError:
            return ValidationResult(False, "Invalid votes_count value")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "votes_count": int(value.get('votes_count', 0)),
            "voters": value.get('voters', []),
            "voted_by_me": value.get('voted_by_me', False)
        }

class ItemIDColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            item_id = str(value)
            if not item_id.strip():
                return ValidationResult(False, "Item ID cannot be empty")
            return ValidationResult(True, transformed_value=item_id)
        except:
            return ValidationResult(False, "Invalid Item ID format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"id": str(value)}

class AutoNumberColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            number = int(value)
            if number < 0:
                return ValidationResult(False, "Auto number must be positive")
            return ValidationResult(True, transformed_value=number)
        except ValueError:
            return ValidationResult(False, "Invalid auto number format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"number": int(value)}

class TimelineColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if not isinstance(value, dict):
            return ValidationResult(False, "Timeline value must be a dictionary")
            
        try:
            from_date = datetime.fromisoformat(str(value.get('from')).replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(str(value.get('to')).replace('Z', '+00:00'))
            
            if to_date < from_date:
                return ValidationResult(False, "End date cannot be before start date")
                
            return ValidationResult(True, transformed_value=value)
        except ValueError:
            return ValidationResult(False, "Invalid date format in timeline")
        except Exception as e:
            return ValidationResult(False, f"Timeline validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "from": value['from'],
            "to": value['to']
        }

class HourColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, str):
                hours, minutes = value.split(':')
                hours = int(hours)
                minutes = int(minutes)
                
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
                
                if not (1 <= week <= 53):
                    return ValidationResult(False, "Week must be between 1 and 53")
                if year < 1900:
                    return ValidationResult(False, "Invalid year")
                    
                return ValidationResult(True, transformed_value={"week": week, "year": year})
            return ValidationResult(False, "Week value must be a dictionary")
        except ValueError:
            return ValidationResult(False, "Invalid week/year format")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "week": value.get('week'),
            "year": value.get('year', datetime.now().year)
        }

class DocumentColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('url'):
                return ValidationResult(False, "Document must have a URL")
            return ValidationResult(True, transformed_value=value)
        return ValidationResult(False, "Document value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {
            "url": value.get('url'),
            "title": value.get('title', ''),
            "file_id": value.get('file_id', '')
        }

# Actualizado el mapping de tipos de columna a handlers
COLUMN_TYPE_HANDLERS = {
    "name": TextColumnHandler(),
    "text": TextColumnHandler(),
    "long_text": LongTextColumnHandler(),
    "numeric": NumberColumnHandler(),
    "date": DateColumnHandler(),
    "email": EmailColumnHandler(),
    "location": LocationColumnHandler(),
    "checkbox": CheckboxColumnHandler(),
    "status": StatusColumnHandler(),
    "dropdown": DropdownColumnHandler(),
    "tags": TagsColumnHandler(),
    "link": LinkColumnHandler(),
    "world_clock": WorldClockColumnHandler(),
    "country": CountryColumnHandler(),
    "phone": PhoneColumnHandler(),
    "rating": RatingColumnHandler(),
    "file": FileColumnHandler(),
    "formula": FormulaColumnHandler(),
    "connect_boards": ConnectBoardsColumnHandler(),
    "creation_log": CreationLogColumnHandler(),
    "dependency": DependencyColumnHandler(),
    "time_tracking": TimeTrackingColumnHandler(),
    "color_picker": ColorPickerColumnHandler(),
    "button": ButtonColumnHandler(),
    "last_updated": LastUpdatedColumnHandler(),
    "mirror": MirrorColumnHandler(),
    "progress": ProgressColumnHandler(),
    "vote": VoteColumnHandler(),
    "item_id": ItemIDColumnHandler(),
    "auto_number": AutoNumberColumnHandler(),
    "timeline": TimelineColumnHandler(),
    "hour": HourColumnHandler(),
    "week": WeekColumnHandler(),
    "doc": DocumentColumnHandler()
}