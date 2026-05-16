"""
unit tests for the suitability quiz engine (task 3.1 / task 6.1).
tests scoring logic, profile classification, and question integrity.

updated for the expanded 36-question quiz.
"""
import pytest
from app.application.services.quiz_service import QuizService
from app.application.services.quiz_questions import QUIZ_QUESTIONS
from app.domain.entities.quiz import QuizResponse


class TestQuizQuestionIntegrity:
    """verify the quiz data matches the expanded specification."""

    def test_has_36_questions(self):
        """quiz was expanded from 28 to 36 questions."""
        assert len(QUIZ_QUESTIONS) == 36

    def test_has_correct_sections(self):
        """quiz must have distinct sections."""
        sections = set(q["section"] for q in QUIZ_QUESTIONS)
        assert len(sections) >= 7

    def test_each_question_has_options(self):
        """each question must have at least 2 options."""
        for q in QUIZ_QUESTIONS:
            assert len(q["options"]) >= 2, f"question {q['id']} has {len(q['options'])} options"

    def test_option_scores_valid(self):
        """every option score must be a positive integer."""
        for q in QUIZ_QUESTIONS:
            for opt in q["options"]:
                assert opt["score"] >= 1, (
                    f"question {q['id']}, option {opt['id']}: score {opt['score']} invalid"
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
        assert len(questions) == 36

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
        """choosing all score=1 options → conservador."""
        answers = []
        for q in self.service.get_questions():
            lowest = min(q.options, key=lambda o: o.score)
            answers.append(QuizResponse(question_id=q.id, option_id=lowest.id))
        result = self.service.calculate_result(answers)
        assert result.profile_type == "Conservador"

    def test_all_highest_scores_is_arrojado(self):
        """choosing all highest score options → arrojado."""
        answers = []
        for q in self.service.get_questions():
            highest = max(q.options, key=lambda o: o.score)
            answers.append(QuizResponse(question_id=q.id, option_id=highest.id))
        result = self.service.calculate_result(answers)
        assert result.profile_type == "Arrojado"

    def test_section_scores_tracked(self):
        """section_scores dict must contain entries for each section answered."""
        answers = []
        for q in self.service.get_questions():
            answers.append(QuizResponse(question_id=q.id, option_id=q.options[0].id))
        result = self.service.calculate_result(answers)
        assert len(result.section_scores) >= 7

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
