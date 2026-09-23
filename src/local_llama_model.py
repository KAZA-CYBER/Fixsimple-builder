import subprocess
import tempfile
from pathlib import Path

from model_interface import FixSimpleModel, ModelRequest, ModelResponse


class LocalLlamaModel(FixSimpleModel):
    def __init__(self, model_path: str):
        self.model_path = model_path

    def complete(self, request: ModelRequest) -> ModelResponse:
        prompt = f"""You are the coding model inside FixSimple Builder.

TASK:
{request.task}

CONTEXT:
{request.context}

Return ONLY the complete corrected Python source file.
No markdown fences.
No explanation.
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
