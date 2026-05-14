import pytest
import sys
import os
from argparse import Namespace

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture
def gsm8k_args():
    """Mock args for GSM8K dataset"""
    return Namespace(dataset="GSM8K")


@pytest.fixture
def gsm_hard_args():
    """Mock args for GSM-Hard dataset"""
    return Namespace(dataset="GSM-Hard")


@pytest.fixture
def gpqa_args():
    """Mock args for GPQA dataset"""
    return Namespace(dataset="GPQA")


@pytest.fixture
def mmlu_args():
    """Mock args for MMLU dataset"""
    return Namespace(dataset="MMLU-high_school_physics")


@pytest.fixture
def math_args():
    """Mock args for MATH dataset"""
    return Namespace(dataset="MATH")


@pytest.fixture
def aime_args():
    """Mock args for AIME_2024 dataset"""
    return Namespace(dataset="AIME_2024")


@pytest.fixture
def mock_llm_responses():
    """Mock LLM responses for different datasets"""
    return {
        "gsm8k_correct": "The answer is 42. \\boxed{42}",
        "gsm8k_with_calc": "2 + 2 = 4, so the answer is \\boxed{4}",
        "gsm8k_nested": "The calculation is \\boxed{\\boxed{5}}",
        "gsm8k_no_box": "The answer is 10",
        "gpqa_correct": "The correct answer is **A**",
        "gpqa_paren": "The correct answer is (B)",
        "gpqa_no_mark": "The answer is C",
        "mmlu_correct": "The correct answer is **D**",
        "math_latex": "\\boxed{\\frac{1}{2}}",
        "math_nested": "\\boxed{2 + \\boxed{3}}",
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "choices": [{"message": {"content": "Sample response"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5}
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    class MockCandidate:
        def __init__(self):
            self.finish_reason = 1
            self.content = self

        @property
        def parts(self):
            return [self]

        @property
        def text(self):
            return "Sample response"

    class MockUsage:
        prompt_token_count = 10
        total_tokens = 5

    class MockResponse:
        def __init__(self):
            self.candidates = [MockCandidate()]
            self.usage_metadata = MockUsage()

    return MockResponse()


@pytest.fixture
def model_pricing():
    """Model pricing information"""
    return {
        "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.3},
        "gpt-3.5-turbo-0613": {"prompt": 1.5, "completion": 2.0},
        "gpt-4o-mini": {"prompt": 0.15, "completion": 0.6},
        "default": {"prompt": 0.15, "completion": 0.6},
    }
