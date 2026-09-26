import json
import subprocess

from model_interface import FixSimpleModel, ModelRequest, ModelResponse


class RemoteOpenAIModel(FixSimpleModel):
    supports_patch_edits = True

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 180,
        lifecycle=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.lifecycle = lifecycle

    def complete(self, request: ModelRequest) -> ModelResponse:
        if request.response_contract == "single_file":
            output_instruction = (
                "Return ONLY the complete corrected Python source file.\n"
                "No markdown fences.\n"
                "No explanation."
            )
        elif request.response_contract == "patch_json":
            output_instruction = (
                "Return ONLY valid JSON in exactly this shape:\n"
                '{"patch":{"path":"relative/path.py","old":"exact existing text","new":"replacement text"}}\n'
                "The path must be the requested target file.\n"
                "old must be an exact non-empty substring copied from the current file and must identify the change uniquely.\n"
                "new is the replacement text. Keep the patch as small as possible.\n"
                "Do not include markdown fences or explanation."
            )
        elif request.response_contract == "multi_patch_json":
            output_instruction = (
                "Return ONLY valid JSON in exactly this shape:\n"
                '{"patches":[{"path":"relative/path.py","old":"exact existing text","new":"replacement text"}]}\n'
                "Include exactly one patch for every requested target file.\n"
                "Do not include unrequested paths or duplicate paths.\n"
                "Each old value must be an exact non-empty substring copied from its current file and must identify the change uniquely.\n"
                "Keep every patch as small as possible.\n"
                "Do not include markdown fences or explanation."
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
        elif request.response_contract == "target_selection_json":
            output_instruction = (
                "Return ONLY valid JSON in exactly this shape:\n"
                '{"targets":["relative/path.py"]}\n'
                "Choose only paths present in candidate_files.\n"
                "Do not invent paths or include explanations.\n"
                "Return at most max_targets paths."
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

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0,
            "max_tokens": 4096,
        }

        lease_id = None

        if self.lifecycle is not None:
            lease_id = self.lifecycle.begin_request(
                request_timeout=self.timeout,
            )

        try:
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

        finally:
            if (
                self.lifecycle is not None
                and lease_id is not None
            ):
                self.lifecycle.end_request(lease_id)

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

        choices = body.get("choices")
        if not choices or len(choices) < 1:
            raise RuntimeError(
                "Remote model response missing 'choices' "
                "or 'choices' is empty"
            )

        message = choices[0].get("message")
        if not message:
            raise RuntimeError(
                "Remote model response missing 'message' "
                "in 'choices[0]'"
            )

        content = message.get("content")
        if not content:
            raise RuntimeError(
                "Remote model response missing 'content' "
                "in 'choices[0].message'"
            )

        content = content.strip()

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
