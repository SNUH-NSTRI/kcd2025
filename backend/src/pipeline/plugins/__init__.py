from __future__ import annotations

from typing import Callable, Dict

from .. import models
from .defaults import (
    SyntheticCohortExtractor,
    SyntheticEHRMapper,
    SyntheticLiteratureFetcher,
    SyntheticOutcomeAnalyzer,
    SyntheticReportGenerator,
    SyntheticTrialParser,
)
from .mimic_demo import MimicDemoCohortExtractor, MimicDemoEHRMapper
from .langgraph_parser import LangGraphTrialParser
from .langgraph_search import LangGraphLiteratureFetcher
from .trialist_parser import TrialistParser
from .trialist_mimic_mapper import TrialistMimicMapper
from .comprehensive_report import ComprehensiveReportGenerator

LiteratureFactory = Callable[[], models.LiteratureFetcher]
ParserFactory = Callable[[], models.TrialParser]
MapperFactory = Callable[[], models.EHRMapper]
CohortFactory = Callable[[], models.CohortExtractor]
AnalyzerFactory = Callable[[], models.OutcomeAnalyzer]
ReportFactory = Callable[[], models.ReportGenerator]


class PluginRegistry:
    """Registry holding factories for each pipeline stage implementation."""

    def __init__(self) -> None:
        self._literature: Dict[str, LiteratureFactory] = {}
        self._parser: Dict[str, ParserFactory] = {}
        self._mapper: Dict[str, MapperFactory] = {}
        self._cohort: Dict[str, CohortFactory] = {}
        self._analyzer: Dict[str, AnalyzerFactory] = {}
        self._report: Dict[str, ReportFactory] = {}

    def register_literature(self, name: str, factory: LiteratureFactory) -> None:
        self._literature[name] = factory

    def get_literature(self, name: str) -> models.LiteratureFetcher:
        try:
            factory = self._literature[name]
        except KeyError as exc:
            raise KeyError(f"unknown literature implementation '{name}'") from exc
        return factory()

    def list_literature(self) -> list[str]:
        return sorted(self._literature.keys())

    def register_parser(self, name: str, factory: ParserFactory) -> None:
        self._parser[name] = factory

    def get_parser(self, name: str) -> models.TrialParser:
        try:
            factory = self._parser[name]
        except KeyError as exc:
            raise KeyError(f"unknown parser implementation '{name}'") from exc
        return factory()

    def register_mapper(self, name: str, factory: MapperFactory) -> None:
        self._mapper[name] = factory

    def get_mapper(self, name: str) -> models.EHRMapper:
        try:
            factory = self._mapper[name]
        except KeyError as exc:
            raise KeyError(f"unknown mapper implementation '{name}'") from exc
        return factory()

    def register_cohort(self, name: str, factory: CohortFactory) -> None:
        self._cohort[name] = factory

    def get_cohort(self, name: str) -> models.CohortExtractor:
        try:
            factory = self._cohort[name]
        except KeyError as exc:
            raise KeyError(f"unknown cohort implementation '{name}'") from exc
        return factory()

    def register_analyzer(self, name: str, factory: AnalyzerFactory) -> None:
        self._analyzer[name] = factory

    def get_analyzer(self, name: str) -> models.OutcomeAnalyzer:
        try:
            factory = self._analyzer[name]
        except KeyError as exc:
            raise KeyError(f"unknown analyzer implementation '{name}'") from exc
        return factory()

    def register_report(self, name: str, factory: ReportFactory) -> None:
        self._report[name] = factory

    def get_report(self, name: str) -> models.ReportGenerator:
        try:
            factory = self._report[name]
        except KeyError as exc:
            raise KeyError(f"unknown report implementation '{name}'") from exc
        return factory()

    def list_report(self) -> list[str]:
        return sorted(self._report.keys())


registry = PluginRegistry()

registry.register_literature("synthetic", lambda: SyntheticLiteratureFetcher())
registry.register_literature("langgraph-search", lambda: LangGraphLiteratureFetcher())
registry.register_parser("synthetic", lambda: SyntheticTrialParser())
registry.register_mapper("synthetic", lambda: SyntheticEHRMapper())
registry.register_cohort("synthetic", lambda: SyntheticCohortExtractor())
registry.register_analyzer("synthetic", lambda: SyntheticOutcomeAnalyzer())
registry.register_report("synthetic", lambda: SyntheticReportGenerator())
registry.register_report("comprehensive", lambda: ComprehensiveReportGenerator())
registry.register_mapper("mimic-demo", lambda: MimicDemoEHRMapper())
registry.register_mapper("trialist-mimic", lambda: TrialistMimicMapper())
registry.register_cohort("mimic-demo", lambda: MimicDemoCohortExtractor())
registry.register_parser("langgraph", lambda: LangGraphTrialParser())
registry.register_parser("trialist", lambda: TrialistParser())


__all__ = ["registry"]
