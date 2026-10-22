"""
Download GGUF/LLM from HuggingFace when not present locally.
"""
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download


def modelLoad(
    llmsPath: Path,
    modelRepo: str,
    modelFile: str,
    llmsDir: Path,
) -> None:
    if not llmsPath.exists():
        print(f"❗ Model not found locally, downloading from HuggingFace: {modelRepo}")
        try:
            downloaded = hf_hub_download(
                repo_id=modelRepo,
                filename=modelFile,
                local_dir=str(llmsDir),
                local_dir_use_symlinks=False,
            )
            print(f"✅ Downloaded model to: {downloaded}")
        except Exception as e:
            print(f"❌ Failed to download model: {e}")
            sys.exit(1)
    else:
        print(f"✅ Model found: {llmsPath}")
