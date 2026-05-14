from typing import List, Dict
from ..domain.entities.quiz import QuizQuestion, QuizOption, QuizResult, QuizResponse
from .quiz_questions import QUIZ_QUESTIONS

class QuizService:
    """
    Service to manage the Suitability Quiz (CEA Level).
    """

    def __init__(self):
        self.questions = self._load_questions()

    def get_questions(self) -> List[QuizQuestion]:
        return self.questions

    def calculate_result(self, answers: List[QuizResponse]) -> QuizResult:
        total_score = 0
        section_scores = {}
        
        q_map = {q.id: q for q in self.questions}
        
        for ans in answers:
            q = q_map.get(ans.question_id)
            if not q: continue
            
            opt = next((o for o in q.options if o.id == ans.option_id), None)
            if not opt: continue
            
            total_score += opt.score
            section_scores[q.section] = section_scores.get(q.section, 0) + opt.score

        # Profile classification based on total score (28 to 112)
        if total_score <= 45:
            profile = "Conservador"
        elif total_score <= 85:
            profile = "Moderado"
        else:
            profile = "Arrojado"

        return QuizResult(
            total_score=total_score,
            profile_type=profile,
            answers=answers,
            section_scores=section_scores
        )

    def _load_questions(self) -> List[QuizQuestion]:
        questions = []
        for q_data in QUIZ_QUESTIONS:
            options = [QuizOption(**opt) for opt in q_data["options"]]
            questions.append(QuizQuestion(
                id=q_data["id"],
                text=q_data["text"],
                section=q_data["section"],
                options=options
            ))
        return questions
