import argparse
import json
from pathlib import Path

from approved_execution import execute_approved_run
from local_llama_model import LocalLlamaModel
from remote_openai_model import RemoteOpenAIModel
from target_approval import approve_discovery_run


DEFAULT_REMOTE_MODEL = (
    "Qwen/Qwen2.5-Coder-14B-Instruct-AWQ"
)
DEFAULT_LOCAL_MODEL = Path(
    "models/granite-4.0-1b-Q4_K_M.gguf"
)


def build_model(
    *,
    backend: str,
    model_path: Path | None = None,
    base_url: str | None = None,
    remote_model: str = DEFAULT_REMOTE_MODEL,
):
    if backend == "local":
        path = (model_path or DEFAULT_LOCAL_MODEL).resolve()
        if not path.exists():
            raise FileNotFoundError(
                f"model does not exist: {path}"
            )
        return LocalLlamaModel(str(path)), path.stem

    if backend == "remote":
        if not base_url:
            raise ValueError(
                "base_url is required for remote backend"
            )
        return (
            RemoteOpenAIModel(
                base_url=base_url,
                model=remote_model,
            ),
            remote_model,
        )

    raise ValueError(f"unsupported backend: {backend}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="FixSimple Builder Run Control"
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    approve = subparsers.add_parser(
        "approve",
        help="approve discovery targets for execution",
    )
    approve.add_argument("--repo", type=Path, required=True)
    approve.add_argument("--run", type=Path, required=True)
    approve.add_argument(
        "--targets",
        nargs="+",
        required=True,
    )

    execute = subparsers.add_parser(
        "execute",
        help="execute a previously approved run",
    )
    execute.add_argument("--repo", type=Path, required=True)
    execute.add_argument("--run", type=Path, required=True)
    execute.add_argument(
        "--backend",
        choices=("local", "remote"),
        default="local",
    )
    execute.add_argument("--model", type=Path, default=None)
    execute.add_argument("--base-url", default=None)
    execute.add_argument(
        "--remote-model",
        default=DEFAULT_REMOTE_MODEL,
    )

    args = parser.parse_args(argv)

    if args.command == "approve":
        approval = approve_discovery_run(
            args.repo,
            args.run,
            args.targets,
        )
        print(json.dumps(approval, indent=2))
        return 0

    model, model_name = build_model(
        backend=args.backend,
        model_path=args.model,
        base_url=args.base_url,
        remote_model=args.remote_model,
    )

    report = execute_approved_run(
        args.repo,
        args.run,
        model,
        model_name=model_name,
    )
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
