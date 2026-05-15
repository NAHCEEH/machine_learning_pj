"""Template for future RAGAS evaluation.

This file intentionally contains only the basic structure. Add real questions,
ground-truth answers, and retrieved contexts when the dataset is ready.
"""

from datasets import Dataset


def build_eval_dataset() -> Dataset:
    """Create a placeholder dataset compatible with RAGAS."""
    samples = {
        "question": [
            "AI 연구자에게 추천할 수업은 무엇인가요?",
            "데이터 분석가에게 가장 관련 있는 수업은 무엇인가요?",
        ],
        "answer": [
            "TODO: RAG pipeline answer",
            "TODO: RAG pipeline answer",
        ],
        "contexts": [
            ["TODO: retrieved course descriptions"],
            ["TODO: retrieved course descriptions"],
        ],
        "ground_truth": [
            "TODO: expected answer",
            "TODO: expected answer",
        ],
    }
    return Dataset.from_dict(samples)


def run_ragas_evaluation() -> None:
    """Run RAGAS metrics after installing/configuring RAGAS.

    Planned metrics:
    - Faithfulness
    - Answer Relevancy
    - Context Recall
    """
    # Example for future implementation:
    # from ragas import evaluate
    # from ragas.metrics import faithfulness, answer_relevancy, context_recall
    #
    # dataset = build_eval_dataset()
    # result = evaluate(
    #     dataset,
    #     metrics=[faithfulness, answer_relevancy, context_recall],
    # )
    # print(result)
    raise NotImplementedError("RAGAS 평가 데이터셋이 준비된 후 구현하세요.")


if __name__ == "__main__":
    print(build_eval_dataset())
