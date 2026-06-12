import logging
import re


class TextPostProcessor:
    def __init__(self, strip_trailing_period: bool = False, corrections: dict = None):
        self.strip_trailing_period = strip_trailing_period
        self.logger = logging.getLogger(__name__)
        self.replacements = {}
        self.corrections_regex = None
        if corrections:
            self._compile_corrections(corrections)

    def _compile_corrections(self, corrections: dict):
        for replacement, variants in corrections.items():
            if isinstance(variants, str):
                variants = [variants]
            for variant in variants:
                self.replacements[str(variant).lower()] = str(replacement)

        variants_longest_first = sorted(self.replacements, key=len, reverse=True)
        pattern = "|".join(re.escape(variant) for variant in variants_longest_first)
        self.corrections_regex = re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)
        self.logger.info(f"Loaded {len(self.replacements)} text corrections")

    def _lookup_replacement(self, match: re.Match) -> str:
        return self.replacements[match.group().lower()]

    def process(self, text: str) -> str:
        if self.corrections_regex:
            text = self.corrections_regex.sub(self._lookup_replacement, text)

        if self.strip_trailing_period and text.endswith('.'):
            text = text[:-1]

        return text
