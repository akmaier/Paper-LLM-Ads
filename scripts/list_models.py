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
from llm_ads_repro.config_loader import force_openai_endpoint, load_llm_api_toml


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--use-openai",
        action="store_true",
        help="Talk to OpenAI's API directly (pops OPENAI_BASE_URL).",
    )
    args = p.parse_args()
    load_dotenv()
    load_llm_api_toml()
    if args.use_openai:
        force_openai_endpoint()
    client = get_client()
    ids = list_chat_model_ids(client)
    print(json.dumps({"base_url": str(client.base_url), "models": ids}, indent=2))


if __name__ == "__main__":
    main()
