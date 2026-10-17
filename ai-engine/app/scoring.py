"""Priority score of an alert.

The score is computed by a fixed formula (brief, section 7). The language model
never computes it: its label can only add points, never remove them.
"""
from dataclasses import dataclass
from enum import Enum

# Wazuh rule levels go from 0 to 15.
MAX_RULE_LEVEL = 15


class Level(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LlmLabel(str, Enum):
    MALICIOUS = "malicious"
    SUSPICIOUS = "suspicious"
    BENIGN = "benign"


@dataclass(frozen=True)
class Weights:
    """Maximum points of each component (starting weights from the brief)."""

    severity: float = 50.0
    misp: float = 25.0
    anomaly: float = 15.0
    llm: float = 10.0


@dataclass(frozen=True)
class Thresholds:
    """Boundaries between levels.

    Placeholder values: the brief leaves them to be calibrated on the test
    scenarios (an SSH brute force must end high, a harmless unusual activity low).
    """

    medium: float = 25.0
    high: float = 40.0


# Share of the LLM weight given by each label. "suspicious" at half weight is an
# assumption of this implementation; the brief only fixes malicious (adds) and
# benign (removes nothing).
LLM_LABEL_SHARE = {
    LlmLabel.MALICIOUS: 1.0,
    LlmLabel.SUSPICIOUS: 0.5,
    LlmLabel.BENIGN: 0.0,
}


@dataclass(frozen=True)
class ScoreDetail:
    severity: float
    misp: float
    anomaly: float
    llm: float

    @property
    def base(self) -> float:
        """Score available before the language model answers."""
        return self.severity + self.misp + self.anomaly

    @property
    def total(self) -> float:
        return self.base + self.llm


def compute_score(
    rule_level: int,
    misp_match: bool,
    anomaly_score: float,
    llm_label: LlmLabel | None = None,
    weights: Weights = Weights(),
) -> ScoreDetail:
    """Return the score components. ``anomaly_score`` is between 0 (normal) and 1."""
    if not 0 <= rule_level <= MAX_RULE_LEVEL:
        raise ValueError(f"rule_level must be between 0 and {MAX_RULE_LEVEL}")
    if not 0.0 <= anomaly_score <= 1.0:
        raise ValueError("anomaly_score must be between 0 and 1")

    llm_points = 0.0
    if llm_label is not None:
        llm_points = weights.llm * LLM_LABEL_SHARE[llm_label]

    return ScoreDetail(
        severity=weights.severity * rule_level / MAX_RULE_LEVEL,
        misp=weights.misp if misp_match else 0.0,
        anomaly=weights.anomaly * anomaly_score,
        llm=llm_points,
    )


def level_for(score: float, thresholds: Thresholds = Thresholds()) -> Level:
    if score >= thresholds.high:
        return Level.HIGH
    if score >= thresholds.medium:
        return Level.MEDIUM
    return Level.LOW


def respond(detail: ScoreDetail, thresholds: Thresholds = Thresholds()) -> bool:
    """True when the final level is high: an automatic response is executed."""
    return level_for(detail.total, thresholds) is Level.HIGH


def respond_before_llm(detail: ScoreDetail, thresholds: Thresholds = Thresholds()) -> bool:
    """True when the base score alone is high: the response must not wait for the LLM."""
    return level_for(detail.base, thresholds) is Level.HIGH
