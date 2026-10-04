import re
from dataclasses import dataclass, field
from typing import List, Set, Optional, Tuple
from router.query_analyzer import QueryAnalysis

# Precision-First Stop Words: standard functional words that do not represent core domain concepts
STOP_WORDS: Set[str] = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "what", "which", "who", "whom", "where", "when", "why", "how",
    "difference", "differences", "between", "and", "or", "vs", "versus",
    "explain", "describe", "summarize", "tell", "me", "about", "give",
    "can", "you", "please", "would", "could", "should", "of", "in", "to",
    "for", "with", "on", "at", "by", "from", "up", "about", "into", "over",
    "after", "it", "its", "do", "does", "did", "have", "has", "had",
    "compare", "comparison", "define", "definition", "overview", "briefly",
    "city", "state", "country"
}

# Dynamic / Time-Sensitive patterns that should NEVER be served from stale semantic cache
DYNAMIC_PATTERNS = [
    r"\bcurrent\s+(price|rate|cost|weather|temperature|stock|value|status|news|president|prime minister)\b",
    r"\bprice\s+of\b",
    r"\bstock\s+price\b",
    r"\btoday\b",
    r"\btonight\b",
    r"\bright\s+now\b",
    r"\bat\s+present\b",
    r"\blatest\b",
    r"\brecent\s+news\b",
    r"\bbreaking\s+news\b",
    r"\blive\s+score\b",
    r"\byesterday\b",
    r"\btomorrow\b"
]

# Constraint & Scoping patterns that narrow the query scope
CONSTRAINT_PATTERNS = [
    r"\bspecifically\s+for\b",
    r"\bin\s+terms\s+of\b",
    r"\bwith\s+respect\s+to\b",
    r"\bunder\s+(condition|conditions|the\s+hood)\b",
    r"\bfocusing\s+on\b",
    r"\bespecially\s+for\b",
    r"\bin\s+the\s+context\s+of\b",
    r"\bas\s+applied\s+to\b",
    r"\bfrom\s+the\s+perspective\s+of\b",
    r"\bin\s+\d{3,4}\b",       # Temporal year constraints, e.g. "in 1800"
    r"\bduring\s+the\s+\d{2,4}s?\b"
]

# High-depth reasoning / mathematical derivation keywords
HIGH_DEPTH_WORDS = {
    "derive", "derivation", "mathematically", "formal proof", "prove",
    "convergence condition", "step-by-step derivation", "rigorous",
    "mathematical proof", "time complexity proof"
}

@dataclass
class CompatibilityResult:
    is_compatible: bool
    reason: str
    similarity: float = 0.0
    detected_constraints: List[str] = field(default_factory=list)
    missing_entities: List[str] = field(default_factory=list)

class CompatibilityChecker:
    """
    Stage 2 Validation: Conservative Compatibility Checker.
    Enforces the Precision > Hit Rate mandate:
    Ensures that high semantic similarity alone does NOT trigger false cache hits
    when queries have different entities, added constraints, temporal modifiers,
    or increased reasoning depth.
    """

    @classmethod
    def is_dynamic_or_time_sensitive(cls, query: str) -> bool:
        """Detects if query requires real-time / dynamic information."""
        q_lower = query.lower()
        for pattern in DYNAMIC_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False

    @classmethod
    def extract_core_terms(cls, query: str) -> Set[str]:
        """Extracts core domain keywords and entities excluding functional stop words."""
        cleaned = re.sub(r"[^\w\s-]", " ", query.lower())
        tokens = cleaned.split()
        return {t for t in tokens if len(t) > 1 and t not in STOP_WORDS}

    @classmethod
    def extract_constraints(cls, query: str) -> List[str]:
        """Extracts scoping modifiers and constraint clauses."""
        q_lower = query.lower()
        found: List[str] = []
        for pattern in CONSTRAINT_PATTERNS:
            matches = re.findall(pattern, q_lower)
            if matches:
                found.extend(matches)
        return found

    @classmethod
    def extract_numbers_and_years(cls, query: str) -> Set[str]:
        """Extracts digits, numbers, and years."""
        return set(re.findall(r"\b\d+\b", query))

    def validate(
        self,
        new_query: str,
        cached_query: str,
        similarity: float,
        threshold: float,
        new_analysis: Optional[QueryAnalysis] = None,
        cached_task_type: Optional[str] = None
    ) -> CompatibilityResult:
        """
        Validates whether a cached response is truly compatible with the new query.
        Returns CompatibilityResult with is_compatible=True only if ALL conservative checks pass.
        """
        # Rule 0: Cosine similarity threshold check (Stage 1 prerequisite)
        if similarity < threshold:
            return CompatibilityResult(
                is_compatible=False,
                reason=f"Similarity {similarity:.4f} is below configured threshold {threshold:.4f}.",
                similarity=similarity
            )

        # Rule 1: Freshness / Dynamic check (prevent serving stale data for time-sensitive queries)
        if self.is_dynamic_or_time_sensitive(new_query):
            return CompatibilityResult(
                is_compatible=False,
                reason="Query is dynamic or time-sensitive (freshness risk). Preferred cache miss.",
                similarity=similarity
            )

        # Rule 2: Temporal & Numerical compatibility (e.g. "capital of France" vs "capital of France in 1800")
        new_numbers = self.extract_numbers_and_years(new_query)
        cached_numbers = self.extract_numbers_and_years(cached_query)
        new_unmatched_numbers = new_numbers - cached_numbers
        if new_unmatched_numbers:
            return CompatibilityResult(
                is_compatible=False,
                reason=f"New query introduces specific numerical or temporal constraints not in cached entry: {new_unmatched_numbers}",
                similarity=similarity
            )

        # Rule 3: Scoping and Constraint Modifier additions (e.g. "specifically for high-latency networks")
        new_constraints = self.extract_constraints(new_query)
        cached_constraints = self.extract_constraints(cached_query)
        added_constraints = [c for c in new_constraints if c not in cached_constraints]
        if added_constraints:
            return CompatibilityResult(
                is_compatible=False,
                reason=f"New query contains scoping constraints not present in cached query: {added_constraints}",
                similarity=similarity,
                detected_constraints=added_constraints
            )

        # Rule 4: Reasoning Depth and Mathematical Derivation requirement
        new_lower = new_query.lower()
        cached_lower = cached_query.lower()
        new_has_high_depth = any(w in new_lower for w in HIGH_DEPTH_WORDS)
        cached_has_high_depth = any(w in cached_lower for w in HIGH_DEPTH_WORDS)

        if new_has_high_depth and not cached_has_high_depth:
            return CompatibilityResult(
                is_compatible=False,
                reason="New query requires high-depth mathematical derivation/reasoning not provided by cached answer.",
                similarity=similarity
            )

        # Rule 5: Entity and Key Concept compatibility (e.g. "decorators" vs "generators")
        new_terms = self.extract_core_terms(new_query)
        cached_terms = self.extract_core_terms(cached_query)
        unmatched_new_terms = new_terms - cached_terms

        # If the new query introduces domain terms that the cached query never mentioned,
        # it is asking about a different concept or adding a domain dimension
        if unmatched_new_terms:
            return CompatibilityResult(
                is_compatible=False,
                reason=f"New query specifies key concepts/entities not in cached query: {unmatched_new_terms}",
                similarity=similarity,
                missing_entities=list(unmatched_new_terms)
            )

        # Rule 6: Task Type / Complexity compatibility from QueryAnalyzer
        if new_analysis and cached_task_type:
            if new_analysis.complexity == "high" and cached_task_type != "reasoning":
                return CompatibilityResult(
                    is_compatible=False,
                    reason=f"Task complexity mismatch: new query is '{new_analysis.complexity}', cached is '{cached_task_type}'.",
                    similarity=similarity
                )

        # All conservative checks passed!
        return CompatibilityResult(
            is_compatible=True,
            reason="High semantic similarity and verified semantic compatibility (entities, constraints, and task matched).",
            similarity=similarity
        )

# Global default instance
compatibility_checker = CompatibilityChecker()
