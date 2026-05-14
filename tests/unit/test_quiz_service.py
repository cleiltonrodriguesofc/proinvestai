"""
unit tests for the suitability quiz engine (task 3.1 / task 6.1).
tests scoring logic, profile classification, and question integrity.
"""
import pytest
from app.application.services.quiz_service import QuizService
from app.application.services.quiz_questions import QUIZ_QUESTIONS
from app.domain.entities.quiz import QuizResponse


class TestQuizQuestionIntegrity:
    """verify the quiz data matches the implementation plan spec."""

    def test_has_28_questions(self):
        """plan requires 7 sections x 4 questions = 28."""
        assert len(QUIZ_QUESTIONS) == 28

    def test_has_7_sections(self):
        """plan requires 7 distinct sections."""
        sections = set(q["section"] for q in QUIZ_QUESTIONS)
        assert len(sections) == 7

    def test_each_question_has_4_options(self):
        """each question must have exactly 4 options."""
        for q in QUIZ_QUESTIONS:
            assert len(q["options"]) == 4, f"question {q['id']} has {len(q['options'])} options"

    def test_option_scores_range_1_to_4(self):
        """every option score must be between 1 and 4."""
        for q in QUIZ_QUESTIONS:
            for opt in q["options"]:
                assert 1 <= opt["score"] <= 4, (
                    f"question {q['id']}, option {opt['id']}: score {opt['score']} out of range"
                )

    def test_question_ids_unique(self):
        """all question ids must be unique."""
        ids = [q["id"] for q in QUIZ_QUESTIONS]
        assert len(ids) == len(set(ids))

    def test_option_ids_unique_within_question(self):
        """option ids must be unique within each question."""
        for q in QUIZ_QUESTIONS:
            opt_ids = [o["id"] for o in q["options"]]
            assert len(opt_ids) == len(set(opt_ids)), f"duplicate option ids in {q['id']}"


class TestQuizServiceLoading:
    """verify QuizService correctly loads and hydrates questions."""

    def setup_method(self):
        self.service = QuizService()

    def test_loads_all_questions(self):
        questions = self.service.get_questions()
        assert len(questions) == 28

    def test_questions_are_domain_objects(self):
        from app.domain.entities.quiz import QuizQuestion
        questions = self.service.get_questions()
        for q in questions:
            assert isinstance(q, QuizQuestion)


class TestQuizScoring:
    """verify the scoring and classification logic."""

    def setup_method(self):
        self.service = QuizService()

    def test_all_lowest_scores_is_conservador(self):
        """choosing all score=1 options → total 28 → conservador."""
        answers = []
        for q in self.service.get_questions():
            lowest = min(q.options, key=lambda o: o.score)
            answers.append(QuizResponse(question_id=q.id, option_id=lowest.id))
        result = self.service.calculate_result(answers)
        assert result.profile_type == "Conservador"
        assert result.total_score == 28

    def test_all_highest_scores_is_arrojado(self):
        """choosing all score=4 options → total 112 → arrojado."""
        answers = []
        for q in self.service.get_questions():
            highest = max(q.options, key=lambda o: o.score)
            answers.append(QuizResponse(question_id=q.id, option_id=highest.id))
        result = self.service.calculate_result(answers)
        assert result.profile_type == "Arrojado"
        assert result.total_score == 112

    def test_middle_scores_is_moderado(self):
        """choosing all score=2 options → total 56 → moderado."""
        answers = []
        for q in self.service.get_questions():
            # pick the option with score=2
            opt = next((o for o in q.options if o.score == 2), q.options[1])
            answers.append(QuizResponse(question_id=q.id, option_id=opt.id))
        result = self.service.calculate_result(answers)
        assert result.profile_type == "Moderado"

    def test_section_scores_tracked(self):
        """section_scores dict must contain entries for each section answered."""
        answers = []
        for q in self.service.get_questions():
            answers.append(QuizResponse(question_id=q.id, option_id=q.options[0].id))
        result = self.service.calculate_result(answers)
        assert len(result.section_scores) == 7

    def test_empty_answers_returns_conservador(self):
        """no answers → score 0 → conservador."""
        result = self.service.calculate_result([])
        assert result.total_score == 0
        assert result.profile_type == "Conservador"

    def test_invalid_question_id_ignored(self):
        """answers with non-existent question ids should be skipped."""
        answers = [QuizResponse(question_id="qXXX", option_id="oXXX")]
        result = self.service.calculate_result(answers)
        assert result.total_score == 0

    def test_invalid_option_id_ignored(self):
        """answers with valid question but invalid option should be skipped."""
        answers = [QuizResponse(question_id="q1", option_id="oXXX")]
        result = self.service.calculate_result(answers)
        assert result.total_score == 0
