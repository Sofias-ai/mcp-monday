from typing import TypeVar, Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum

class ValueOperator(Enum):
    ANY_OF = "any_of"
    NOT_ANY_OF = "not_any_of"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    CONTAINS_TEXT = "contains_text"
    NOT_CONTAINS_TEXT = "not_contains_text"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUALS = "greater_than_or_equals"
    LOWER_THAN = "lower_than"
    LOWER_THAN_OR_EQUALS = "lower_than_or_equals"
    BETWEEN = "between"

# Añadidas nuevas enumeraciones para tipos específicos
class FormulaType(Enum):
    NUMBER = "number"
    TEXT = "text"
    DATE = "date"
    TIME = "time"
    BOOLEAN = "boolean"

class MirrorType(Enum):
    ITEMS = "items"
    SUBITEMS = "subitems"

class TimeTrackingStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"

@dataclass
class ValidationResult:
    is_valid: bool
    message: Optional[str] = None
    transformed_value: Any = None
    suggested_values: Optional[List[str]] = None

@dataclass
class ColumnSettings:
    type: str
    title: str
    settings: Dict[str, Any]
    allowed_values: Optional[List[str]] = None
    validation_rules: Optional[Dict[str, Any]] = None

@dataclass
class ColumnValue:
    raw_value: Any
    formatted_value: Any
    validation_result: ValidationResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary"""
        return {
            "raw_value": self.raw_value,
            "formatted_value": self.formatted_value,
            "validation_result": {
                "is_valid": self.validation_result.is_valid,
                "message": self.validation_result.message,
                "transformed_value": self.validation_result.transformed_value,
                "suggested_values": self.validation_result.suggested_values
            }
        }

# Nuevas clases para tipos específicos de columnas
@dataclass
class FormulaValue:
    formula: str
    result_type: FormulaType
    result: Any
    error: Optional[str] = None

@dataclass
class ConnectBoardsValue:
    board_id: str
    item_ids: List[str]
    linked_board_name: Optional[str] = None

@dataclass
class TimeTrackingValue:
    status: TimeTrackingStatus
    duration: int  # en segundos
    started_at: Optional[str] = None
    ended_at: Optional[str] = None

@dataclass
class MirrorValue:
    source_board_id: str
    mirror_type: MirrorType
    filters: Optional[Dict[str, Any]] = None

@dataclass
class ButtonValue:
    label: str
    action_id: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None

@dataclass
class CreationLogValue:
    created_by: str
    created_at: str
    account_id: Optional[str] = None

@dataclass
class LastUpdatedValue:
    updated_by: str
    updated_at: str
    account_id: Optional[str] = None

@dataclass
class DependencyValue:
    depends_on: List[str]  # item IDs
    required_for: List[str]  # item IDs
    blocking: bool = False

@dataclass
class ProgressValue:
    progress: float  # 0-100
    auto_progress: bool = False

@dataclass
class VoteValue:
    votes_count: int
    voters: List[str]  # user IDs
    voted_by_me: bool = False

@dataclass
class ColorPickerValue:
    color: str  # hex code
    label: Optional[str] = None

@dataclass
class ColumnFormat:
    """Format specification for a column"""
    column_type: str
    settings: Dict[str, Any]
    validation_rules: Optional[Dict[str, Any]] = None

@dataclass
class ColumnDefinition:
    """Complete column definition"""
    id: str
    title: str
    format: ColumnFormat
    handler_class: Optional[str] = None

# Tipos compuestos
JsonValue = Union[str, int, float, bool, Dict[str, Any], List[Any], None]

# Tipo base para valores de columna
ColumnValueType = Union[
    str, int, float, bool, Dict[str, Any],
    FormulaValue, ConnectBoardsValue, TimeTrackingValue,
    MirrorValue, ButtonValue, CreationLogValue,
    LastUpdatedValue, DependencyValue, ProgressValue,
    VoteValue, ColorPickerValue
]