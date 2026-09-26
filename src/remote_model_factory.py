from remote_openai_model import RemoteOpenAIModel
from runpod_lifecycle import RunPodLifecycleManager


def build_remote_model(
    *,
    base_url: str,
    model: str,
    timeout: int = 180,
    environ=None,
):
    lifecycle = RunPodLifecycleManager.from_env(
        base_url=base_url,
        environ=environ,
    )

    return RemoteOpenAIModel(
        base_url=base_url,
        model=model,
        timeout=timeout,
        lifecycle=lifecycle,
    )
