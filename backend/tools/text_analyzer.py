from collections import Counter
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from .base import BaseTool, ToolResult


class TextAnalyzer(BaseTool):
    """Deterministic tool for text metrics (word count, char count, sentence count, word frequency)."""

    name = "text_analyzer"
    description = "Computes deterministic text metrics (word count, character count, sentence count, frequency) without an LLM."

    # Pattern 1: [operation] of/in/for "<text>"
    _pattern_quoted = re.compile(
        r'^(?:(?:what\s+is\s+the|calculate\s+the|get\s+the|find\s+the)\s+)?'
        r'(word\s+count|character\s+count|char\s+count|sentence\s+count|word\s+frequency|most\s+common\s+words|analyze\s+text|text\s+stats)\s+'
        r'(?:in|of|for)\s+["\'](.+?)["\']\??$',
        re.IGNORECASE
    )

    # Pattern 2: [operation]: <text>
    _pattern_colon = re.compile(
        r'^(?:(?:what\s+is\s+the|calculate\s+the|get\s+the|find\s+the)\s+)?'
        r'(word\s+count|character\s+count|char\s+count|sentence\s+count|word\s+frequency|most\s+common\s+words|analyze\s+text|text\s+stats)\s*'
        r':\s*(.+)$',
        re.IGNORECASE
    )

    # Pattern 3: how many [words/characters/sentences] in "<text>"
    _pattern_how_many = re.compile(
        r'^how\s+many\s+(words|characters|chars|sentences)\s+(?:are\s+)?(?:in|of)\s+["\'](.+?)["\']\??$',
        re.IGNORECASE
    )

    # Pattern 4: count [words/characters/sentences] in/of: "<text>" or : <text>
    _pattern_count_prefixed = re.compile(
        r'^count\s+(words|characters|chars|sentences)\s+(?:in|of)\s*(?::\s*["\']?|["\'])(.+?)(?:["\'])?\??$',
        re.IGNORECASE
    )

    # Pattern 5: unquoted [operation] in/of <text>
    _pattern_unquoted = re.compile(
        r'^(?:(?:what\s+is\s+the|calculate\s+the|get\s+the|find\s+the)\s+)?'
        r'(word\s+count|character\s+count|char\s+count|sentence\s+count|word\s+frequency|most\s+common\s+words|analyze\s+text|text\s+stats)\s+'
        r'(?:in|of|for)\s+(.+?)\??$',
        re.IGNORECASE
    )

    # Question phrases that indicate general QA rather than text analysis payload
    _qa_phrases = {
        "the english language", "the dictionary", "the bible", "a novel", "a book", "a human",
        "the world", "average", "typical", "standard", "normal", "a sentence", "a paragraph"
    }

    def _normalize_operation(self, op_raw: str) -> str:
        s = op_raw.strip().lower()
        if s in ("word count", "words", "count words"):
            return "word_count"
        if s in ("character count", "char count", "characters", "chars", "count characters", "count chars"):
            return "character_count"
        if s in ("sentence count", "sentences", "count sentences"):
            return "sentence_count"
        if s in ("word frequency", "most common words", "top words"):
            return "word_frequency"
        if s in ("analyze text", "text stats"):
            return "summary"
        return s

    def parse_query(self, query: str) -> Optional[Tuple[str, str]]:
        """Extracts (operation, target_text) from query."""
        q = query.strip()

        m1 = self._pattern_quoted.match(q)
        if m1:
            return self._normalize_operation(m1.group(1)), m1.group(2).strip()

        m2 = self._pattern_colon.match(q)
        if m2:
            return self._normalize_operation(m2.group(1)), m2.group(2).strip()

        m3 = self._pattern_how_many.match(q)
        if m3:
            return self._normalize_operation(m3.group(1)), m3.group(2).strip()

        m4 = self._pattern_count_prefixed.match(q)
        if m4:
            return self._normalize_operation(m4.group(1)), m4.group(2).strip()

        m5 = self._pattern_unquoted.match(q)
        if m5:
            op_raw, payload = m5.groups()
            payload_clean = payload.strip().lower()
            # If payload looks like a knowledge question, reject
            if any(phrase in payload_clean for phrase in self._qa_phrases):
                return None
            if payload_clean.startswith(("a ", "an ", "the ")) and len(payload_clean.split()) <= 4:
                return None
            return self._normalize_operation(op_raw), payload.strip()

        return None

    def can_handle(self, query: str) -> bool:
        """Conservatively check if the query is a valid deterministic text analysis task."""
        parsed = self.parse_query(query)
        if not parsed:
            return False

        _, text = parsed
        # Must have actual text content to analyze
        return len(text.strip()) > 0

    # Explicit text extraction definitions:
    def extract_words(self, text: str) -> List[str]:
        """Extracts words defined as contiguous sequences of alphanumeric characters and hyphens/apostrophes."""
        return re.findall(r"\b[a-zA-Z0-9_\'-]+\b", text)

    def extract_sentences(self, text: str) -> List[str]:
        """Extracts sentences delimited by ., !, or ? punctuation."""
        raw_sentences = re.split(r'[.!?]+(?:\s+|$)', text.strip())
        return [s.strip() for s in raw_sentences if s.strip()]

    def count_characters(self, text: str) -> Dict[str, int]:
        """Counts total characters including and excluding whitespace."""
        return {
            "total": len(text),
            "no_spaces": len(re.sub(r'\s+', '', text))
        }

    def compute_word_frequency(self, text: str) -> Dict[str, int]:
        """Computes case-insensitive word frequencies sorted by count descending."""
        words = [w.lower() for w in self.extract_words(text)]
        return dict(Counter(words).most_common())

    def analyze(self, op: str, text: str) -> Any:
        """Performs the requested text analysis operation."""
        words = self.extract_words(text)
        sentences = self.extract_sentences(text)
        chars = self.count_characters(text)

        if op == "word_count":
            return len(words)

        elif op == "character_count":
            return chars["total"]

        elif op == "sentence_count":
            return len(sentences)

        elif op == "word_frequency":
            return self.compute_word_frequency(text)

        elif op == "summary":
            freq = self.compute_word_frequency(text)
            avg_word_len = round(sum(len(w) for w in words) / len(words), 2) if words else 0.0
            return {
                "word_count": len(words),
                "character_count_total": chars["total"],
                "character_count_no_spaces": chars["no_spaces"],
                "sentence_count": len(sentences),
                "average_word_length": avg_word_len,
                "top_words": dict(list(freq.items())[:5]),
            }

        raise ValueError(f"Unsupported text analysis operation: '{op}'")

    def execute(self, query: str) -> ToolResult:
        """Executes text analysis and returns ToolResult."""
        start_time = time.perf_counter()
        parsed = self.parse_query(query)

        if not parsed:
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=False,
                result=None,
                tool_name=self.name,
                execution_time_ms=exec_time,
                error="Could not parse a valid text analysis query.",
                metadata={"calls_llm": False, "query": query},
            )

        op, text = parsed
        try:
            val = self.analyze(op, text)
            exec_time = (time.perf_counter() - start_time) * 1000
            return ToolResult(
                success=True,
                result=val,
                tool_name=self.name,
                execution_time_ms=exec_time,
                metadata={
                    "operation": op,
                    "target_text_length": len(text),
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
