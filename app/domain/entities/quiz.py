from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class QuizOption:
    id: str
    text: str
    score: int  # 1-4 scale usually


@dataclass
class QuizQuestion:
    id: str
    text: str
    section: str
    options: List[QuizOption]


@dataclass
class QuizResponse:
    question_id: str
    option_id: str


@dataclass
class QuizResult:
    total_score: int
    profile_type: str  # Conservador, Moderado, Arrojado
    answers: List[QuizResponse]
    section_scores: Dict[str, int] = field(default_factory=dict)
