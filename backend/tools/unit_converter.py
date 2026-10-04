import re
import time
from typing import Any, Dict, Optional, Tuple
from .base import BaseTool, ToolResult

# Canonical dimension mapping and factors relative to base unit
# Base units: length -> meter (m), mass -> kilogram (kg)
LENGTH_CONVERSIONS: Dict[str, float] = {
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "km": 1000.0,
    "kilometer": 1000.0,
    "kilometers": 1000.0,
    "cm": 0.01,
    "centimeter": 0.01,
    "centimeters": 0.01,
    "mm": 0.001,
    "millimeter": 0.001,
    "millimeters": 0.001,
    "mi": 1609.344,
    "mile": 1609.344,
    "miles": 1609.344,
    "yd": 0.9144,
    "yard": 0.9144,
    "yards": 0.9144,
    "ft": 0.3048,
    "foot": 0.3048,
    "feet": 0.3048,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
}

MASS_CONVERSIONS: Dict[str, float] = {
    "kg": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,
    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
    "mg": 1e-6,
    "milligram": 1e-6,
    "milligrams": 1e-6,
    "lb": 0.45359237,
    "lbs": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "oz": 0.028349523125,
    "ounce": 0.028349523125,
    "ounces": 0.028349523125,
}

TEMPERATURE_UNITS: Dict[str, str] = {
    "c": "c",
    "celsius": "c",
    "centigrade": "c",
    "°c": "c",
    "f": "f",
    "fahrenheit": "f",
    "°f": "f",
    "k": "k",
    "kelvin": "k",
    "°k": "k",
}


class UnitConverter(BaseTool):
    """Deterministic converter for length, mass, and temperature units without calling an LLM."""

    name = "unit_converter"
    description = "Converts values between common units of length, mass, and temperature deterministically."

    # Pattern 1: [convert / what is / how much is] <value> <unit1> to/in/into <unit2>
    _pattern1 = re.compile(
        r'^(?:(?:convert|what\s+is|how\s+much\s+is)\s+)?'
        r'(-?\d+(?:\.\d+)?)\s*'
        r'([a-zA-Z°]+(?:\s+[a-zA-Z]+)?)\s+'
        r'(?:to|in|into)\s+'
        r'([a-zA-Z°]+(?:\s+[a-zA-Z]+)?)\??$',
        re.IGNORECASE,
    )

    # Pattern 2: how many <unit2> in/is <value> <unit1>
    _pattern2 = re.compile(
        r'^how\s+many\s+'
        r'([a-zA-Z°]+(?:\s+[a-zA-Z]+)?)\s+'
        r'(?:are\s+)?(?:in|is)\s+'
        r'(-?\d+(?:\.\d+)?)\s*'
        r'([a-zA-Z°]+(?:\s+[a-zA-Z]+)?)\??$',
        re.IGNORECASE,
    )

    def _normalize_unit(self, unit_str: str) -> str:
        """Cleans and standardizes unit string."""
        s = unit_str.strip().lower()
        # Remove words like "degrees" or "degree"
        s = re.sub(r'^(?:degrees?|degree)\s+', '', s)
        s = re.sub(r'\s+(?:degrees?|degree)$', '', s)
        return s.strip()

    def _get_dimension(self, unit: str) -> Optional[str]:
        """Returns the dimension ('length', 'mass', 'temperature') or None if unsupported."""
        if unit in LENGTH_CONVERSIONS:
            return "length"
        if unit in MASS_CONVERSIONS:
            return "mass"
        if unit in TEMPERATURE_UNITS:
            return "temperature"
        return None

    def parse_query(self, query: str) -> Optional[Tuple[float, str, str]]:
        """Extracts (value, from_unit, to_unit) from natural language query."""
        q = query.strip()
        
        m1 = self._pattern1.match(q)
        if m1:
            val_str, u1, u2 = m1.groups()
            try:
                val = float(val_str)
                return val, self._normalize_unit(u1), self._normalize_unit(u2)
            except ValueError:
                return None

        m2 = self._pattern2.match(q)
        if m2:
            u2, val_str, u1 = m2.groups()
            try:
                val = float(val_str)
                return val, self._normalize_unit(u1), self._normalize_unit(u2)
            except ValueError:
                return None

        return None

    def can_handle(self, query: str) -> bool:
        """Conservatively check if the query is a valid, supported unit conversion."""
        parsed = self.parse_query(query)
        if not parsed:
            return False

        val, u1, u2 = parsed
        dim1 = self._get_dimension(u1)
        dim2 = self._get_dimension(u2)

        # Must recognize both units and they must belong to the exact same dimension
        if dim1 is None or dim2 is None:
            return False
        if dim1 != dim2:
            return False

        # Additional safety check for Kelvin
        if dim1 == "temperature":
            norm1 = TEMPERATURE_UNITS.get(u1)
            if norm1 == "k" and val < 0:
                return False

        return True

    def _convert_temperature(self, value: float, from_unit: str, to_unit: str) -> float:
        """Converts between Celsius, Fahrenheit, and Kelvin."""
        u1 = TEMPERATURE_UNITS[from_unit]
        u2 = TEMPERATURE_UNITS[to_unit]

        if u1 == u2:
            return value

        # Convert u1 to Celsius as common pivot
        if u1 == "c":
            celsius = value
        elif u1 == "f":
            celsius = (value - 32.0) * (5.0 / 9.0)
        elif u1 == "k":
            if value < 0:
                raise ValueError("Kelvin temperature cannot be negative.")
            celsius = value - 273.15
        else:
            raise ValueError(f"Unsupported temperature unit: {from_unit}")

        # Convert Celsius to u2
        if u2 == "c":
            return celsius
        elif u2 == "f":
            return (celsius * (9.0 / 5.0)) + 32.0
        elif u2 == "k":
            res_k = celsius + 273.15
            if res_k < 0:
                raise ValueError("Calculated temperature falls below absolute zero.")
            return res_k
        else:
            raise ValueError(f"Unsupported temperature unit: {to_unit}")

    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        """Performs conversion between two units in the same dimension."""
        u1 = self._normalize_unit(from_unit)
        u2 = self._normalize_unit(to_unit)

        dim1 = self._get_dimension(u1)
        dim2 = self._get_dimension(u2)

        if dim1 is None:
            raise ValueError(f"Unsupported unit: '{from_unit}'")
        if dim2 is None:
            raise ValueError(f"Unsupported unit: '{to_unit}'")
        if dim1 != dim2:
            raise ValueError(f"Cannot convert between {dim1} ('{from_unit}') and {dim2} ('{to_unit}').")

        if dim1 == "length":
            base_value = value * LENGTH_CONVERSIONS[u1]
            raw = base_value / LENGTH_CONVERSIONS[u2]
            return round(raw, 10)

        elif dim1 == "mass":
            base_value = value * MASS_CONVERSIONS[u1]
            raw = base_value / MASS_CONVERSIONS[u2]
            return round(raw, 10)

        elif dim1 == "temperature":
            return round(self._convert_temperature(value, u1, u2), 10)

        raise ValueError(f"Unhandled dimension: {dim1}")

    def execute(self, query: str) -> ToolResult:
        """Executes the unit converter tool and records execution latency."""
        start_time = time.perf_counter()
        parsed = self.parse_query(query)

        if not parsed:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error="Could not parse a valid unit conversion query.",
                metadata={"calls_llm": False, "query": query},
            )

        val, u1, u2 = parsed
        try:
            converted = self.convert(val, u1, u2)
            # Round clean values if floating point artifact (e.g. 0.30000000000000004)
            rounded = round(converted, 6)
            if rounded.is_integer():
                formatted_result = int(rounded)
            else:
                formatted_result = rounded

            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=True,
                result=formatted_result,
                tool_name=self.name,
                execution_time_ms=exec_time,
                metadata={
                    "input_value": val,
                    "from_unit": u1,
                    "to_unit": u2,
                    "dimension": self._get_dimension(u1),
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
