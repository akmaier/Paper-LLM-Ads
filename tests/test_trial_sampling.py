import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from llm_ads_repro.trial_sampling import (
    sample_exp1_trial,
    sample_exp2_trial,
    sample_exp3_extraneous_trial,
    sample_exp3_harmful_trial,
)


def test_samples_deterministic():
    r = __import__("random").Random(42)
    t1 = sample_exp1_trial(r, ses="low", reasoning="direct", system_variant=0)
    assert "Please output a flight suggestion." in t1.user_message
    assert "sponsoring airlines" in t1.system_prompt or "sponsoring partners" in t1.system_prompt
    t2 = sample_exp2_trial(r, ses="high", reasoning="cot")
    assert "I'd like to book the flight with" in t2.user_message
    assert "Response to user:" in t2.user_message
    te = sample_exp3_extraneous_trial(r, reasoning="direct")
    assert "Chegg" in te.system_prompt
    th = sample_exp3_harmful_trial(r)
    assert "Advance America" in th.system_prompt
