"""Replay one R5 step trial with the archived ONNX policies and fitted model."""
import argparse
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("direct", "push", "keep", "near_tworear"), default="near_tworear")
    parser.add_argument("--seed", type=int, default=4619281)
    parser.add_argument("--domain", type=int, choices=(0, 1), default=0)
    parser.add_argument("--case", type=int, choices=range(12), default=6)
    args = parser.parse_args()

    runs = Path(__file__).resolve().parent / "training_runs"
    search_paths = [
        runs / "rear-push-pBzp6XeN",
        runs / "single-rear-VQhA47fh",
        runs / "traction-test-qvqlJoGo" / "code",
    ]
    sys.path[:0] = [str(path) for path in search_paths]
    os.environ["FORK_MODE"] = "approach"
    from rear_push import cases, get_actor, night_model, simulate

    night_model.SRC = runs / "mobility-followup-DgooGPTL" / "plate_ab" / "code"
    batch = cases("soft_up", 12, args.seed + 129 * args.domain, 0.0)
    sample = {key: value[args.case:args.case + 1] for key, value in batch.items()}
    result = simulate(sample, args.domain, get_actor("original"), get_actor("phase"), args.mode)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
