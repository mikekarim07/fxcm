SCHEMA_VERSION = "1.0"


SHEET_SCHEMAS = {
    "App_Config": [
        "schema_version",
        "app_id",
        "currency",
        "initial_balance",
        "initial_date",
        "calendar_type",
        "display_timezone",
        "created_at_utc",
    ],

    "Plan_Versions": [
        "version_id",
        "version_no",
        "previous_version_id",
        "created_at_utc",
        "effective_date",
        "starting_balance",
        "target_balance",
        "end_date",
        "peak_position",
        "curve_intensity",
    ],

    "Actual_Events": [
        "event_id",
        "business_date",
        "event_type",
        "actual_pnl",
        "supersedes_event_id",
        "historical_target_pnl",
        "historical_target_balance",
        "target_plan_version_id",
        "target_forecast_revision_id",
        "created_at_utc",
    ],

    "Forecast_Revisions": [
        "revision_id",
        "revision_no",
        "created_at_utc",
        "trigger_type",
        "trigger_id",
        "plan_version_id",
        "confirmed_through_date",
        "anchor_balance",
        "effective_from_date",
        "curve_position_at_anchor",
        "data_status",
    ],
}
