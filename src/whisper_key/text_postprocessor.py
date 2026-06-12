import logging
import re


class TextPostProcessor:
    def __init__(self, strip_trailing_period: bool = False, corrections: dict = None):
        self.strip_trailing_period = strip_trailing_period
        self.logger = logging.getLogger(__name__)
        self.replacements = {}
        self.corrections_regex = None
        if isinstance(corrections, dict):
            self._compile_corrections(corrections)
        elif corrections:
            self.logger.warning(f"Ignoring corrections config: expected a mapping, got {type(corrections).__name__}")

    def _compile_corrections(self, corrections: dict):
        for replacement, variants in corrections.items():
            if variants is None:
                continue
            if not isinstance(variants, list):
                variants = [variants]
            for variant in variants:
                variant = str(variant).strip()
                if variant:
                    self.replacements[variant.casefold()] = str(replacement)

        if not self.replacements:
            return

        variants_longest_first = sorted(self.replacements, key=len, reverse=True)
        pattern = "|".join(re.escape(variant) for variant in variants_longest_first)
        self.corrections_regex = re.compile(rf"\b(?:{pattern})\b", re.IGNORECASE)
        self.logger.info(f"Loaded {len(self.replacements)} text corrections")

    def _lookup_replacement(self, match: re.Match) -> str:
        return self.replacements.get(match.group().casefold(), match.group())

    def process(self, text: str) -> str:
        if self.corrections_regex:
            text = self.corrections_regex.sub(self._lookup_replacement, text)

        if self.strip_trailing_period and text.endswith('.'):
            text = text[:-1]

        return text
