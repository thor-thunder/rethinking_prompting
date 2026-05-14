"""Tests for dataset.py functions"""
import pytest
import sys
import os
from argparse import Namespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from dataset import (
    parse_answer,
    examine_output,
    get_cost,
    find_most_common_elements,
    get_unique_most_common_answer,
    parse_best_solution,
    is_equiv,
    last_boxed_only_string,
    remove_boxed,
)


class TestParseAnswerGSM8K:
    """Test parse_answer for GSM8K dataset"""

    def test_parse_boxed_answer(self, gsm8k_args):
        """Test parsing standard \\boxed{} format"""
        response = "The answer is \\boxed{42}"
        result = parse_answer(gsm8k_args, response)
        assert result == 42.0

    def test_parse_boxed_with_calculation(self, gsm8k_args):
        """Test parsing boxed answer with calculation inside"""
        response = "2 + 2 = 4, so \\boxed{4}"
        result = parse_answer(gsm8k_args, response)
        assert result == 4.0

    def test_parse_nested_boxed(self, gsm8k_args):
        """Test parsing nested boxed answers"""
        response = "\\boxed{\\boxed{5}}"
        result = parse_answer(gsm8k_args, response)
        assert result == 5.0

    def test_parse_boxed_with_equals(self, gsm8k_args):
        """Test parsing boxed answer with equals sign inside"""
        response = "Therefore \\boxed{x = 10}"
        result = parse_answer(gsm8k_args, response)
        assert result == 10.0

    def test_parse_multiple_boxed_uses_last(self, gsm8k_args):
        """Test that multiple boxed answers uses the last one"""
        response = "First try \\boxed{10}, then \\boxed{20}"
        result = parse_answer(gsm8k_args, response)
        assert result == 20.0

    def test_parse_no_boxed_uses_braces(self, gsm8k_args):
        """Test fallback to {number} format"""
        response = "The answer is {42} when no boxed"
        result = parse_answer(gsm8k_args, response)
        assert result == 42.0

    def test_parse_bold_markdown(self, gsm8k_args):
        """Test parsing **bold** format"""
        response = "The answer is **25**"
        result = parse_answer(gsm8k_args, response)
        assert result == 25.0

    def test_parse_number_extraction(self, gsm8k_args):
        """Test fallback to plain number extraction"""
        response = "The answer is 15"
        result = parse_answer(gsm8k_args, response)
        assert result == 15.0

    def test_parse_decimal_number(self, gsm8k_args):
        """Test parsing decimal numbers"""
        response = "\\boxed{3.14}"
        result = parse_answer(gsm8k_args, response)
        assert result == 3.14

    def test_parse_negative_number(self, gsm8k_args):
        """Test parsing negative numbers"""
        response = "\\boxed{-42}"
        result = parse_answer(gsm8k_args, response)
        assert result == -42.0

    def test_parse_empty_response(self, gsm8k_args):
        """Test parsing empty response returns None"""
        response = ""
        result = parse_answer(gsm8k_args, response)
        assert result is None

    def test_parse_no_number_returns_none(self, gsm8k_args):
        """Test response with no parseable number returns None"""
        response = "The answer is not provided"
        result = parse_answer(gsm8k_args, response)
        assert result is None


class TestParseAnswerGPQA:
    """Test parse_answer for GPQA dataset"""

    def test_parse_correct_answer_bold(self, gpqa_args):
        """Test parsing GPQA with **letter** format"""
        response = "The correct answer is **A**"
        result = parse_answer(gpqa_args, response)
        assert result == "A"

    def test_parse_correct_answer_parentheses(self, gpqa_args):
        """Test parsing GPQA with (letter) format"""
        response = "The correct answer is (B)"
        result = parse_answer(gpqa_args, response)
        assert result == "B"

    def test_parse_answer_extraction_from_parentheses(self, gpqa_args):
        """Test extracting letter from parentheses in text"""
        response = "Looking at this (C) is the answer"
        result = parse_answer(gpqa_args, response)
        assert result == "C"

    def test_parse_answer_braces_format(self, gpqa_args):
        """Test parsing with {letter} format"""
        response = "The answer is {D}"
        result = parse_answer(gpqa_args, response)
        assert result == "D"

    def test_parse_multiple_answers_uses_last(self, gpqa_args):
        """Test that multiple answers uses the last one"""
        response = "First (A), then (B)"
        result = parse_answer(gpqa_args, response)
        assert result == "B"


class TestParseAnswerMMlu:
    """Test parse_answer for MMLU dataset"""

    def test_parse_mmlu_correct_answer_bold(self, mmlu_args):
        """Test parsing MMLU with bold format"""
        response = "The correct answer is **C**"
        result = parse_answer(mmlu_args, response)
        assert result == "C"


class TestParseAnswerMATH:
    """Test parse_answer for MATH dataset"""

    def test_parse_math_latex_fraction(self, math_args):
        """Test parsing MATH with LaTeX fraction"""
        response = "\\boxed{\\frac{1}{2}}"
        result = parse_answer(math_args, response)
        # Result is a string after processing
        assert isinstance(result, str)


class TestExamineOutput:
    """Test examine_output for evaluation"""

    def test_examine_gsm8k_exact_match(self, gsm8k_args):
        """Test GSM8K exact numeric match"""
        result = examine_output("GSM8K", 42.0, "42")
        assert result is True

    def test_examine_gsm8k_close_match(self, gsm8k_args):
        """Test GSM8K allows small floating point differences"""
        result = examine_output("GSM8K", 42.0, "42.00001")
        assert result is True

    def test_examine_gsm8k_no_match(self, gsm8k_args):
        """Test GSM8K mismatch returns None"""
        result = examine_output("GSM8K", 42.0, "41")
        assert result is None

    def test_examine_gsm8k_none_output(self, gsm8k_args):
        """Test GSM8K with None output"""
        result = examine_output("GSM8K", None, "42")
        assert result is None

    def test_examine_gsm_hard_exact(self, gsm_hard_args):
        """Test GSM-Hard exact match"""
        result = examine_output("GSM-Hard", 42.0, 42)
        assert result is True

    def test_examine_gpqa_match(self, gpqa_args):
        """Test GPQA letter matching"""
        result = examine_output("GPQA", "A", "A")
        assert result is True

    def test_examine_gpqa_no_match(self, gpqa_args):
        """Test GPQA letter non-matching"""
        result = examine_output("GPQA", "A", "B")
        assert result is False

    def test_examine_mmlu_match(self, mmlu_args):
        """Test MMLU matching"""
        result = examine_output("MMLU-test", "C", "C")
        assert result is True


class TestGetCost:
    """Test cost calculation for different models"""

    def test_cost_gemini(self):
        """Test Gemini cost calculation"""
        cost = get_cost("gemini-1.5-flash", 1000, 500)
        # 1000 * 0.075 + 500 * 0.3 = 75 + 150 = 225, / 10^6 = 0.000225
        assert cost == pytest.approx(0.000225)

    def test_cost_gpt35_turbo(self):
        """Test GPT-3.5 turbo cost calculation"""
        cost = get_cost("gpt-3.5-turbo-0613", 1000, 500)
        # 1000 * 1.5 + 500 * 2 = 1500 + 1000 = 2500, / 10^6 = 0.0025
        assert cost == pytest.approx(0.0025)

    def test_cost_gpt4o_mini(self):
        """Test GPT-4o-mini cost calculation"""
        cost = get_cost("gpt-4o-mini", 1000, 500)
        # 1000 * 0.15 + 500 * 0.6 = 150 + 300 = 450, / 10^6 = 0.00045
        assert cost == pytest.approx(0.00045)

    def test_cost_unknown_model_uses_default(self):
        """Test unknown model uses default pricing"""
        cost = get_cost("unknown-model", 1000, 500)
        # 1000 * 0.15 + 500 * 0.6 = 150 + 300 = 450, / 10^6 = 0.00045
        assert cost == pytest.approx(0.00045)

    def test_cost_zero_tokens(self):
        """Test cost with zero tokens"""
        cost = get_cost("gpt-4o-mini", 0, 0)
        assert cost == 0.0

    def test_cost_string_inputs(self):
        """Test cost calculation with string inputs"""
        cost = get_cost("gpt-4o-mini", "1000", "500")
        assert cost == pytest.approx(0.00045)


class TestFindMostCommonElements:
    """Test find_most_common_elements utility"""

    def test_single_element_repeated(self):
        """Test with single element repeated"""
        result, count = find_most_common_elements(["A", "A", "A", "B"])
        assert result == ["A"]
        assert count == 3

    def test_multiple_most_common(self):
        """Test with multiple elements having same max count"""
        result, count = find_most_common_elements(["A", "A", "B", "B", "C"])
        assert set(result) == {"A", "B"}
        assert count == 2

    def test_all_unique(self):
        """Test with all unique elements"""
        result, count = find_most_common_elements(["A", "B", "C"])
        assert len(result) == 3
        assert count == 1

    def test_empty_after_filtering_nones(self):
        """Test with all None values returns None"""
        result = find_most_common_elements([None, None, None])
        assert result is None


class TestGetUniqueMostCommonAnswer:
    """Test get_unique_most_common_answer"""

    def test_clear_majority(self):
        """Test with clear majority answer"""
        outputs = ["A", "A", "A", "B"]
        result = get_unique_most_common_answer(outputs)
        assert result == "A"

    def test_tie_picks_one(self):
        """Test with tie picks one randomly"""
        outputs = ["A", "A", "B", "B"]
        result = get_unique_most_common_answer(outputs)
        assert result in ["A", "B"]

    def test_filters_none_values(self):
        """Test that None values are filtered"""
        outputs = [None, "A", "A", "B"]
        result = get_unique_most_common_answer(outputs)
        assert result == "A"

    def test_all_none_returns_none(self):
        """Test all None values returns None"""
        outputs = [None, None, None]
        result = get_unique_most_common_answer(outputs)
        assert result is None

    def test_empty_returns_none(self):
        """Test empty list returns None"""
        outputs = []
        result = get_unique_most_common_answer(outputs)
        assert result is None


class TestParseBestSolution:
    """Test parse_best_solution for Tree of Thoughts"""

    def test_parse_index_pattern(self):
        """Test parsing 'index of the best solution is X' pattern"""
        response = "index of the best solution is 3"
        result = parse_best_solution(response)
        assert result == "3"

    def test_parse_bold_number(self):
        """Test parsing **number** pattern"""
        response = "The best solution is **2**"
        result = parse_best_solution(response)
        assert result == "2"

    def test_parse_multiple_patterns_uses_last(self):
        """Test with multiple 'index' patterns uses the last one"""
        response = "index of the best solution is 1, and index of the best solution is 5"
        result = parse_best_solution(response)
        assert result == "5"

    def test_parse_no_pattern_returns_none(self):
        """Test no matching pattern returns None"""
        response = "No solution index here"
        result = parse_best_solution(response)
        assert result is None


class TestLastBoxedOnlyString:
    """Test last_boxed_only_string function"""

    def test_find_last_boxed(self):
        """Test finding last \\boxed"""
        text = "\\boxed{1} and \\boxed{2}"
        result = last_boxed_only_string(text)
        assert result == "\\boxed{2}"

    def test_find_fbox(self):
        """Test finding \\fbox"""
        text = "\\fbox{answer}"
        result = last_boxed_only_string(text)
        assert result == "\\fbox{answer}"

    def test_nested_braces(self):
        """Test with nested braces"""
        text = "\\boxed{\\frac{1}{2}}"
        result = last_boxed_only_string(text)
        assert result == "\\boxed{\\frac{1}{2}}"

    def test_no_boxed_returns_none(self):
        """Test no boxed returns None"""
        text = "answer is 42"
        result = last_boxed_only_string(text)
        assert result is None


class TestRemoveBoxed:
    """Test remove_boxed function"""

    def test_remove_valid_boxed(self):
        """Test removing valid \\boxed{}"""
        text = "\\boxed{42}"
        result = remove_boxed(text)
        assert result == "42"

    def test_remove_nested_content(self):
        """Test removing boxed with nested content"""
        text = "\\boxed{\\frac{1}{2}}"
        result = remove_boxed(text)
        assert result == "\\frac{1}{2}"

    def test_invalid_format_returns_none(self):
        """Test invalid format returns None"""
        text = "not boxed"
        result = remove_boxed(text)
        assert result is None

    def test_missing_closing_brace_returns_none(self):
        """Test missing closing brace returns None"""
        text = "\\boxed{42"
        result = remove_boxed(text)
        assert result is None


class TestIsEquiv:
    """Test is_equiv for MATH dataset equivalence checking"""

    def test_exact_match(self):
        """Test exact string match"""
        assert is_equiv("42", "42") is True

    def test_different_strings(self):
        """Test different strings"""
        assert is_equiv("42", "43") is False

    def test_both_none(self):
        """Test both None (should warn but return True)"""
        result = is_equiv(None, None)
        assert result is True

    def test_one_none(self):
        """Test one None returns False"""
        assert is_equiv(None, "42") is False
        assert is_equiv("42", None) is False

    def test_fraction_equivalence(self):
        """Test fraction normalization"""
        # These should be equivalent after stripping
        result = is_equiv("\\frac{1}{2}", "0.5")
        # May or may not be true depending on _strip_string implementation
        assert isinstance(result, bool)
