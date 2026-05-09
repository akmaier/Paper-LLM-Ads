#!/usr/bin/env python3
"""List model ids from an OpenAI-compatible gateway (e.g. NHR@FAU / RRZE)."""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.client import get_client, list_chat_model_ids


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--llmapi-key",
        metavar="KEY",
        default=None,
        help="RRZE/NHR gateway API key (sets LLMAPI_KEY for this run; optional if env/.env has it).",
    )
    args = ap.parse_args()

    load_dotenv()
    if args.llmapi_key:
        os.environ["LLMAPI_KEY"] = args.llmapi_key.strip()
    client = get_client()
    ids = list_chat_model_ids(client)
    print(json.dumps({"base_url": str(client.base_url), "models": ids}, indent=2))


if __name__ == "__main__":
    main()
