from typing import Any, Dict, Optional
from datetime import datetime
import difflib, logging
from monday_types import (ValidationResult, MirrorType)
from monday_validators import (
    validate_location, validate_formula, validate_connect_boards,
    validate_time_tracking, validate_color_picker, validate_dependency,
    validate_progress
)
from monday_column_handlers_basic import ColumnTypeHandler
logger = logging.getLogger('monday_handlers')

class StatusColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        """Validate status value against allowed labels"""
        if "labels" not in settings:
            return ValidationResult(False, "No labels defined for status column")
            
        value_str = str(value)
        settings_labels = settings.get("labels", {})
        
        for label_id, label_text in settings_labels.items():
            if value_str.lower() == str(label_text).lower():
                return ValidationResult(is_valid=True, transformed_value={"label_id": label_id, "text": label_text}, 
                                      message="Valid status value")
                
        valid_values = list(settings_labels.values())
        matches = difflib.get_close_matches(value_str, valid_values, n=3, cutoff=0.6)
        
        if matches:
            return ValidationResult(is_valid=False, 
                                  message=f"Invalid value. Did you mean one of these? {', '.join(matches)}",
                                  suggested_values=matches)
        return ValidationResult(is_valid=False, message=f"Invalid value. Valid options are: {', '.join(valid_values)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        """Transform status according to Monday.com API specs"""
        if "labels" not in settings: raise ValueError("No labels defined in settings")
            
        value_str = str(value).lower()
        for index, label in settings["labels"].items():
            if str(label).lower() == value_str:
                return {"index": str(index)}
                
        raise ValueError(f"Invalid status value: {value}")

    def get_validation_rules(self, settings: Dict) -> Dict[str, Any]:
        rules = super().get_validation_rules(settings)
        rules.update({"allowed_values": list(settings.get("labels", {}).values())})
        return rules

class LocationColumnHandler(ColumnTypeHandler):
    _location_cache = {}
    
    def _get_cached_location(self, address: str) -> Optional[Dict]:
        return self._location_cache.get(address)

    def _cache_location(self, address: str, location_data: Dict):
        self._location_cache[address] = location_data
        if len(self._location_cache) > 1000:
            items_to_remove = int(len(self._location_cache) * 0.1)
            for _ in range(items_to_remove):
                self._location_cache.popitem(last=False)

    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            address = str(value)
            cached = self._get_cached_location(address)
            if cached: return ValidationResult(is_valid=True, transformed_value=cached, message="Location found (cached)")
            
            result = validate_location(value)
            if result.is_valid: self._cache_location(address, result.transformed_value)
            return result
        except Exception as e:
            return ValidationResult(False, f"Location validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        if isinstance(value, dict) and all(k in value for k in ['lat', 'lng', 'address']): return value
            
        address = str(value)
        cached = self._get_cached_location(address)
        if cached: return cached
            
        result = validate_location(value)
        if not result.is_valid:
            return {"lat": "", "lng": "", "address": address}
            
        self._cache_location(address, result.transformed_value)
        return result.transformed_value

class DropdownColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if "labels" not in settings: return ValidationResult(False, "No labels defined for dropdown")
            
        labels = settings["labels"].values()
        value_str = str(value)
        if value_str in labels: return ValidationResult(True, "Valid value")
            
        matches = difflib.get_close_matches(value_str, labels, n=3, cutoff=0.6)
        if matches:
            return ValidationResult(is_valid=False, 
                                  message=f"Invalid value. Did you mean one of these? {', '.join(matches)}",
                                  suggested_values=matches)
        return ValidationResult(is_valid=False, message=f"Invalid value. Valid options are: {', '.join(labels)}")

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

class RatingColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            rating = int(float(value))
            max_rating = settings.get("max_rating", 5)
            if 0 <= rating <= max_rating: return ValidationResult(True, "")
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
        if isinstance(value, list): return {"files": value}
        return {"files": [str(value)]}

class FormulaColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_formula(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        formula_result = validate_formula(value, settings)
        if not formula_result.is_valid: raise ValueError(formula_result.message)
        return formula_result.transformed_value

class ConnectBoardsColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_connect_boards(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        connection_result = validate_connect_boards(value, settings)
        if not connection_result.is_valid: raise ValueError(connection_result.message)
        return connection_result.transformed_value

class TimeTrackingColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_time_tracking(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        tracking_result = validate_time_tracking(value)
        if not tracking_result.is_valid: raise ValueError(tracking_result.message)
        return tracking_result.transformed_value

class ColorPickerColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_color_picker(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        color_result = validate_color_picker(value)
        if not color_result.is_valid: raise ValueError(color_result.message)
        return color_result.transformed_value

class DependencyColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_dependency(value, settings)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        dependency_result = validate_dependency(value, settings)
        if not dependency_result.is_valid: raise ValueError(dependency_result.message)
        return dependency_result.transformed_value

class ProgressColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        return validate_progress(value)

    def transform_value(self, value: Any, settings: Dict) -> Any:
        progress_result = validate_progress(value)
        if not progress_result.is_valid: raise ValueError(progress_result.message)
        return progress_result.transformed_value

class ButtonColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('label'): return ValidationResult(False, "Button must have a label")
            if not value.get('action_id'): return ValidationResult(False, "Button must have an action_id")
            return ValidationResult(True, transformed_value=value)
        return ValidationResult(False, "Button value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"label": value.get('label'), "action_id": value.get('action_id'),
               "target_type": value.get('target_type'), "target_id": value.get('target_id')}

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
        return {"created_by": value['created_by'], "created_at": value['created_at'],
               "account_id": value.get('account_id')}

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
        return {"updated_by": value['updated_by'], "updated_at": value['updated_at'],
               "account_id": value.get('account_id')}

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
        return {"source_board_id": value['source_board_id'], "mirror_type": value['mirror_type'],
               "filters": value.get('filters', {})}

class VoteColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        try:
            if isinstance(value, dict):
                votes_count = int(value.get('votes_count', 0))
                voters = value.get('voters', [])
                if not isinstance(voters, list): return ValidationResult(False, "Voters must be a list")
                return ValidationResult(True, transformed_value={"votes_count": votes_count, "voters": voters})
            return ValidationResult(False, "Vote value must be a dictionary")
        except ValueError:
            return ValidationResult(False, "Invalid votes_count value")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"votes_count": int(value.get('votes_count', 0)), "voters": value.get('voters', []),
               "voted_by_me": value.get('voted_by_me', False)}

class TimelineColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if not isinstance(value, dict):
            return ValidationResult(False, "Timeline value must be a dictionary")
            
        try:
            from_date = datetime.fromisoformat(str(value.get('from')).replace('Z', '+00:00'))
            to_date = datetime.fromisoformat(str(value.get('to')).replace('Z', '+00:00'))
            
            if to_date < from_date: return ValidationResult(False, "End date cannot be before start date")
            return ValidationResult(True, transformed_value=value)
        except ValueError:
            return ValidationResult(False, "Invalid date format in timeline")
        except Exception as e:
            return ValidationResult(False, f"Timeline validation error: {str(e)}")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"from": value['from'], "to": value['to']}

class DocumentColumnHandler(ColumnTypeHandler):
    def validate_value(self, value: Any, settings: Dict) -> ValidationResult:
        if isinstance(value, dict):
            if not value.get('url'): return ValidationResult(False, "Document must have a URL")
            return ValidationResult(True, transformed_value=value)
        return ValidationResult(False, "Document value must be a dictionary")

    def transform_value(self, value: Any, settings: Dict) -> Any:
        return {"url": value.get('url'), "title": value.get('title', ''), "file_id": value.get('file_id', '')}