#!/usr/bin/env python3
"""List model ids from an OpenAI-compatible gateway (e.g. NHR@FAU / RRZE)."""

from __future__ import annotations

import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.client import get_client, list_chat_model_ids


def main() -> None:
    load_dotenv()
    client = get_client()
    ids = list_chat_model_ids(client)
    print(json.dumps({"base_url": str(client.base_url), "models": ids}, indent=2))


if __name__ == "__main__":
    main()
