import json
from pathlib import Path

from app.evaluation.harness import RegressionRunner, synthetic_cases


def main() -> None:
    base_path = Path(__file__).resolve().parents[1]
    runner = RegressionRunner(base_path=base_path)
    result = runner.run(synthetic_cases())

    output_path = base_path / "artifacts" / "phase2_evaluation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8")

    print(json.dumps(result.model_dump(mode="json"), indent=2))
    print(f"Saved evaluation report to: {output_path}")


if __name__ == "__main__":
    main()
