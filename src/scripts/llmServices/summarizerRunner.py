"""
Recursive summarizer: chunk (underthesea) + abstractive (Seq2Seq).
"""
from typing import Dict
import sys
from pathlib import Path

import torch

# Add parent scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.scripts.jsonProcessing import jsonChunkUnder


class RecursiveSummarizer:
    def __init__(
        self,
        tokenizer,
        summarizer,
        sumDevice: str,
        chunkBuilder: json_chunk_under.ChunkUndertheseaBuilder,
        maxLength: int = 256,
        minLength: int = 64,
        maxDepth: int = 5,
    ):
        self.tokenizer = tokenizer
        self.model = summarizer
        self.device = sumDevice
        self.chunkBuilder = chunkBuilder
        self.maxLength = maxLength
        self.minLength = minLength
        self.maxDepth = maxDepth

    def summarizeSingle(self, text: str) -> str:
        if not text or len(text.strip()) == 0:
            return ""
        if "vit5" in str(self.model.__class__).lower():
            input_text = f"vietnews: {text.strip()} </s>"
        else:
            input_text = text.strip()
        try:
            inputs = self.tokenizer(
                input_text,
                return_tensors="pt",
                truncation=True,
                max_length=1024,
            ).to(self.device)
            with torch.no_grad():
                summary_ids = self.model.generate(
                    **inputs,
                    max_length=self.maxLength,
                    min_length=self.minLength,
                    num_beams=4,
                    no_repeat_ngram_size=3,
                    early_stopping=True,
                )
            summary = self.tokenizer.decode(
                summary_ids[0], skip_special_tokens=True
            )
            return summary.strip()
        except torch.cuda.OutOfMemoryError:
            self.model = self.model.to("cpu")
            inputs = inputs.to("cpu")
            with torch.no_grad():
                summary_ids = self.model.generate(
                    **inputs,
                    max_length=self.maxLength,
                    min_length=self.minLength,
                    num_beams=4,
                )
            return self.tokenizer.decode(
                summary_ids[0], skip_special_tokens=True
            ).strip()
        except Exception as e:
            return ""

    def summarizeRecursive(
        self,
        text: str,
        depth: int = 0,
        minInput: int = 256,
        maxInput: int = 1024,
    ) -> str:
        word_count = len(text.split())
        if word_count < minInput:
            return self.summarizeSingle(text)
        chunks = self.chunkBuilder.build(text)
        summaries = []
        for item in chunks:
            content = item.get("Content", "")
            wc = len(content.split())
            if wc < 20:
                continue
            sub_summary = self.summarizeSingle(content)
            if sub_summary:
                summaries.append(sub_summary)
        merged_summary = "\n".join(summaries)
        merged_len = len(merged_summary.split())
        if merged_len > 1024 and depth < self.maxDepth:
            return self.summarizeRecursive(
                merged_summary, depth + 1, minInput=minInput, maxInput=maxInput
            )
        return merged_summary

    def summarize(
        self,
        full_text: str,
        minInput: int = 256,
        maxInput: int = 1024,
    ) -> Dict[str, str]:
        original_len = len(full_text.split())
        summary = self.summarizeRecursive(
            full_text, depth=0, minInput=minInput, maxInput=maxInput
        )
        summary_len = len(summary.split())
        ratio = round(summary_len / original_len, 3) if original_len else 0
        return {
            "summaryText": summary,
            "original_words": original_len,
            "summary_words": summary_len,
            "compression_ratio": ratio,
        }
