import subprocess
import tempfile
from pathlib import Path

from model_interface import FixSimpleModel, ModelRequest, ModelResponse


class LocalLlamaModel(FixSimpleModel):
    def __init__(self, model_path: str):
        self.model_path = model_path

    def complete(self, request: ModelRequest) -> ModelResponse:
        if request.response_contract == "single_file":
            output_instruction = (
                "Return ONLY the complete corrected Python source file.\n"
                "No markdown fences.\n"
                "No explanation."
            )
        elif request.response_contract == "multi_file_json":
            output_instruction = (
                "Return ONLY valid JSON in exactly this shape:\n"
                '{"files":{"relative/path.py":"complete file content"}}\n'
                "Include every requested target file exactly once.\n"
                "Do not include any other files.\n"
                "No markdown fences.\n"
                "No explanation."
            )
        else:
            raise ValueError(
                "unsupported response contract: "
                + request.response_contract
            )

        prompt = f"""You are the coding model inside FixSimple Builder.

TASK:
{request.task}

CONTEXT:
{request.context}

{output_instruction}
"""

        with tempfile.NamedTemporaryFile(
            mode="w+",
            suffix=".txt",
            delete=False,
        ) as tmp:
            output_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "llama", "cli",
                    "-m", self.model_path,
                    "-p", prompt,
                    "-n", "120",
                    "--temp", "0",
                    "--no-display-prompt",
                    "--no-show-timings",
                    "--single-turn",
                    "--simple-io",
                    "--ctx-size", "512",
                    "--batch-size", "64",
                    "--ubatch-size", "64",
                    "--threads", "2",
                    "--output-file", output_path,
                ],
                text=True,
                capture_output=True,
                timeout=180,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    f"Local model failed with exit code {result.returncode}\n"
                    f"STDOUT:\n{result.stdout}\n"
                    f"STDERR:\n{result.stderr}"
                )

            content = Path(output_path).read_text().strip()

            # Keep only the final assistant response.
            if "Assistant:" in content:
                content = content.rsplit("Assistant:", 1)[1].strip()

        finally:
            Path(output_path).unlink(missing_ok=True)

        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        if not content:
            raise RuntimeError("Local model returned empty content")

        return ModelResponse(
            content=content,
            model="granite-4.0-1b-Q4_K_M-local",
        )
