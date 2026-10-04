import calendar
from datetime import date, datetime, timedelta
import re
import time
from typing import Any, Dict, Optional, Tuple
from .base import BaseTool, ToolResult

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %d %Y",
    "%b %d %Y",
    "%d %B %Y",
    "%d %b %Y",
]

class DateTimeCalculator(BaseTool):
    """Deterministic tool for date arithmetic, day differences, day-of-week, and leap-year calculations."""

    name = "datetime_calculator"
    description = "Performs deterministic date arithmetic such as date differences, day additions/subtractions, and day-of-week lookups."

    # Pattern: [how many days between / days between / difference between] <date1> and <date2>
    _diff_pattern = re.compile(
        r'^(?:(?:how\s+many\s+days\s+(?:are\s+)?between|days\s+between|difference\s+between)\s+)'
        r'(.+?)\s+and\s+(.+?)\??$',
        re.IGNORECASE
    )

    # Pattern: [what date is] <N> days/weeks after/before/from <date>
    _offset_pattern1 = re.compile(
        r'^(?:what\s+date\s+is\s+)?'
        r'(\d+)\s*(days?|weeks?)\s+'
        r'(after|from|before|prior\s+to)\s+'
        r'(.+?)\??$',
        re.IGNORECASE
    )

    # Pattern: <date> + / - <N> days/weeks
    _offset_pattern2 = re.compile(
        r'^(.+?)\s*([\+\-])\s*(\d+)\s*(days?|weeks?)\??$',
        re.IGNORECASE
    )

    # Pattern: [what day of the week was/is/for] <date>
    _weekday_pattern = re.compile(
        r'^(?:what\s+(?:is\s+the\s+)?day\s+of\s+(?:the\s+)?week\s+(?:was|is|for)|'
        r'day\s+of\s+(?:the\s+)?week\s+(?:of|for))\s+'
        r'(.+?)\??$',
        re.IGNORECASE
    )

    # Pattern: [is] <year> a leap year
    _leap_pattern = re.compile(
        r'^(?:is\s+)?(\d{1,4})\s+a\s+leap\s+year\??$',
        re.IGNORECASE
    )

    def parse_date(self, date_str: str) -> Optional[date]:
        """Tries to parse a string into a datetime.date using safe supported formats."""
        s = date_str.strip()
        # Clean ordinal suffixes: 1st, 2nd, 3rd, 4th
        s = re.sub(r'(\d+)(?:st|nd|rd|th)\b', r'\1', s)
        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date()
            except ValueError:
                continue
        return None

    def can_handle(self, query: str) -> bool:
        """Conservatively check if the query is a supported deterministic date operation."""
        q = query.strip()

        # Leap year check
        if self._leap_pattern.match(q):
            return True

        # Date difference check
        m_diff = self._diff_pattern.match(q)
        if m_diff:
            d1_str, d2_str = m_diff.groups()
            return self.parse_date(d1_str) is not None and self.parse_date(d2_str) is not None

        # Offset pattern 1: N days after <date>
        m_off1 = self._offset_pattern1.match(q)
        if m_off1:
            _, _, _, date_str = m_off1.groups()
            return self.parse_date(date_str) is not None

        # Offset pattern 2: <date> + N days
        m_off2 = self._offset_pattern2.match(q)
        if m_off2:
            date_str, _, _, _ = m_off2.groups()
            return self.parse_date(date_str) is not None

        # Weekday pattern
        m_day = self._weekday_pattern.match(q)
        if m_day:
            date_str = m_day.group(1)
            return self.parse_date(date_str) is not None

        return False

    def calculate(self, query: str) -> Dict[str, Any]:
        """Executes date calculation logic and returns result dict."""
        q = query.strip()

        # 1. Leap year
        m_leap = self._leap_pattern.match(q)
        if m_leap:
            year = int(m_leap.group(1))
            is_leap = calendar.isleap(year)
            return {
                "operation": "leap_year",
                "year": year,
                "result": f"{year} is a leap year." if is_leap else f"{year} is not a leap year.",
                "is_leap_year": is_leap,
            }

        # 2. Date difference
        m_diff = self._diff_pattern.match(q)
        if m_diff:
            d1_str, d2_str = m_diff.groups()
            d1 = self.parse_date(d1_str)
            d2 = self.parse_date(d2_str)
            if not d1 or not d2:
                raise ValueError(f"Could not parse dates: '{d1_str}', '{d2_str}'.")
            diff_days = abs((d2 - d1).days)
            return {
                "operation": "date_difference",
                "date1": d1.isoformat(),
                "date2": d2.isoformat(),
                "days": diff_days,
                "result": f"{diff_days} days",
            }

        # 3. Date offset (Pattern 1)
        m_off1 = self._offset_pattern1.match(q)
        if m_off1:
            num_str, unit, direction, date_str = m_off1.groups()
            d = self.parse_date(date_str)
            if not d:
                raise ValueError(f"Could not parse date: '{date_str}'.")
            count = int(num_str)
            delta = timedelta(days=count if "day" in unit.lower() else count * 7)
            if direction.lower() in ("before", "prior to"):
                res_date = d - delta
            else:
                res_date = d + delta
            return {
                "operation": "date_offset",
                "base_date": d.isoformat(),
                "offset_days": delta.days if direction.lower() not in ("before", "prior to") else -delta.days,
                "result": res_date.isoformat(),
            }

        # 4. Date offset (Pattern 2)
        m_off2 = self._offset_pattern2.match(q)
        if m_off2:
            date_str, sign, num_str, unit = m_off2.groups()
            d = self.parse_date(date_str)
            if not d:
                raise ValueError(f"Could not parse date: '{date_str}'.")
            count = int(num_str)
            delta = timedelta(days=count if "day" in unit.lower() else count * 7)
            res_date = d + delta if sign == "+" else d - delta
            return {
                "operation": "date_offset",
                "base_date": d.isoformat(),
                "offset_days": delta.days if sign == "+" else -delta.days,
                "result": res_date.isoformat(),
            }

        # 5. Day of week
        m_day = self._weekday_pattern.match(q)
        if m_day:
            date_str = m_day.group(1)
            d = self.parse_date(date_str)
            if not d:
                raise ValueError(f"Could not parse date: '{date_str}'.")
            weekday_name = calendar.day_name[d.weekday()]
            return {
                "operation": "day_of_week",
                "date": d.isoformat(),
                "day_of_week": weekday_name,
                "result": weekday_name,
            }

        raise ValueError("Could not parse a valid date/time calculation query.")

    def execute(self, query: str) -> ToolResult:
        """Executes the date/time tool and records execution latency."""
        start_time = time.perf_counter()
        try:
            calc_data = self.calculate(query)
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=True,
                result=calc_data["result"],
                tool_name=self.name,
                execution_time_ms=exec_time,
                metadata={
                    "operation": calc_data.get("operation"),
                    "details": calc_data,
                    "calls_llm": False,
                },
            )
        except Exception as e:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error=str(e),
                metadata={"calls_llm": False, "query": query},
            )
