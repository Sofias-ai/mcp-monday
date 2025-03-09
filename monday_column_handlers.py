import logging
from monday_column_handlers_basic import (
    ColumnTypeHandler, TextColumnHandler, LongTextColumnHandler, 
    NumberColumnHandler, DateColumnHandler, EmailColumnHandler,
    PhoneColumnHandler, CheckboxColumnHandler, LinkColumnHandler,
    ItemIDColumnHandler, AutoNumberColumnHandler, HourColumnHandler, WeekColumnHandler
)
from monday_column_handlers_advanced import (
    StatusColumnHandler, DropdownColumnHandler, TagsColumnHandler, WorldClockColumnHandler,
    CountryColumnHandler, RatingColumnHandler, FileColumnHandler, FormulaColumnHandler,
    ConnectBoardsColumnHandler, TimeTrackingColumnHandler, ColorPickerColumnHandler,
    ButtonColumnHandler, CreationLogColumnHandler, LastUpdatedColumnHandler,
    MirrorColumnHandler, VoteColumnHandler, TimelineColumnHandler, LocationColumnHandler,
    DependencyColumnHandler, ProgressColumnHandler, DocumentColumnHandler
)

logger = logging.getLogger('monday_handlers')
COLUMN_TYPE_HANDLERS = {
    
    "name": TextColumnHandler(),
    "text": TextColumnHandler(),
    "long_text": LongTextColumnHandler(),
    "numeric": NumberColumnHandler(),
    "date": DateColumnHandler(),
    "email": EmailColumnHandler(),
    "checkbox": CheckboxColumnHandler(),
    "link": LinkColumnHandler(),
    "phone": PhoneColumnHandler(),
    "item_id": ItemIDColumnHandler(),
    "auto_number": AutoNumberColumnHandler(),
    "hour": HourColumnHandler(),
    "week": WeekColumnHandler(),
    
    "status": StatusColumnHandler(),
    "dropdown": DropdownColumnHandler(),
    "tags": TagsColumnHandler(),
    "location": LocationColumnHandler(),
    "world_clock": WorldClockColumnHandler(),
    "country": CountryColumnHandler(),
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
    "timeline": TimelineColumnHandler(),
    "doc": DocumentColumnHandler()
}

__all__ = ['ColumnTypeHandler', 'COLUMN_TYPE_HANDLERS']