from app_code.content.models import FilterRule


class SqliteDialect:
    _FIELDS = {"region": "region_code"}

    def render(self, rule: FilterRule) -> str:
        column = self._FIELDS.get(rule.field)
        if column is None or rule.operator != "contains":
            raise ValueError("Unsupported filter")

        pattern = f"%{rule.value}%"
        return (
            "SELECT record_id, display_name, region_code, priority, health_url "
            "FROM integrations "
            "WHERE enabled = 1 "
            f"AND {column} LIKE '{pattern}' "
            "ORDER BY priority, record_id"
        )
