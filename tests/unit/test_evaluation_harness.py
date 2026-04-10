from pathlib import Path

from app.evaluation.harness import RegressionRunner, synthetic_cases


def test_synthetic_dataset_size() -> None:
    cases = synthetic_cases()
    assert 20 <= len(cases) <= 50


def test_regression_runner_returns_expected_metrics_shape() -> None:
    base_path = Path(__file__).resolve().parents[2]
    runner = RegressionRunner(base_path=base_path)
    result = runner.run(synthetic_cases()[:3])
    assert result.metrics.total_cases == 3
    assert 0.0 <= result.metrics.policy_correctness <= 1.0
    assert 0.0 <= result.metrics.approval_routing_correctness <= 1.0
    assert 0.0 <= result.metrics.risk_classification_consistency <= 1.0
    assert 0.0 <= result.metrics.budget_enforcement_correctness <= 1.0
    assert 0.0 <= result.metrics.policy_trace_correctness <= 1.0
    assert 0.0 <= result.metrics.approval_lifecycle_correctness <= 1.0
