import json
import subprocess

from model_interface import FixSimpleModel, ModelRequest, ModelResponse


class RemoteOpenAIModel(FixSimpleModel):
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 180,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

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

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0,
            "max_tokens": 512,
        }

        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--fail-with-body",
                "--max-time",
                str(self.timeout),
                f"{self.base_url}/v1/chat/completions",
                "-X",
                "POST",
                "-H",
                "Content-Type: application/json",
                "-H",
                "Accept: application/json",
                "-d",
                json.dumps(payload),
            ],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Remote model request failed\n"
                f"exit={result.returncode}\n"
                f"stdout={result.stdout}\n"
                f"stderr={result.stderr}"
            )

        try:
            body = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Remote model returned invalid JSON:\n"
                + result.stdout
            ) from exc

        content = (
            body["choices"][0]["message"]["content"].strip()
        )

        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        if not content:
            raise RuntimeError(
                "Remote model returned empty content"
            )

        return ModelResponse(
            content=content,
            model=self.model,
        )
