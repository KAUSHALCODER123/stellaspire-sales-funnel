import json

from sslib.sync import sync_plan


def thread(tid, to, ours, labels=()):
    return {"thread_id": tid, "to": to, "our_messages": ours, "labels": list(labels)}


def test_a_new_sent_thread_gets_step_1_and_its_campaign_from_the_ledger():
    out = sync_plan({"threads": [thread("t1", "A@Acme.in", 1)], "ledger": [{"email": "a@acme.in", "campaign": "pune-sales"}]})
    assert out == {"actions": [{"thread_id": "t1", "add": ["SS/Step-1", "SS/C-pune-sales"]}], "unmatched": []}


def test_a_follow_up_advances_the_step_and_keeps_the_campaign():
    out = sync_plan({"threads": [thread("t1", "a@acme.in", 3, ["SS/Step-2", "SS/C-pune-sales"])]})
    assert out["actions"] == [{"thread_id": "t1", "add": ["SS/Step-3"]}] and out["unmatched"] == []


def test_a_thread_already_labelled_correctly_needs_nothing_and_steps_stop_at_5():
    assert sync_plan({"threads": [thread("t1", "a@acme.in", 2, ["SS/Step-2", "SS/C-x"])]}) == {"actions": [], "unmatched": []}
    out = sync_plan({"threads": [thread("t2", "a@acme.in", 9, ["SS/Step-4", "SS/C-x"])]})
    assert out["actions"] == [{"thread_id": "t2", "add": ["SS/Step-5"]}]


def test_imported_leads_map_to_the_imported_campaign_without_a_ledger(config_dir):
    (config_dir / "imported-leads.json").write_text(json.dumps({"leads": [{"contact": {"email": "Rohit@Jupiter.money"}}]}))
    (config_dir / "campaigns.json").write_text(json.dumps({"campaigns": [
        {"slug": "existing-leads", "name": "E", "status": "active", "source": "imported", "target_contacts": 5, "start_date": "2026-11-27"}]}))
    out = sync_plan({"threads": [thread("t1", "rohit@jupiter.money", 1)]})
    assert out["actions"] == [{"thread_id": "t1", "add": ["SS/Step-1", "SS/C-existing-leads"]}]


def test_an_unknown_recipient_still_gets_its_step_but_is_reported_without_a_campaign():
    out = sync_plan({"threads": [thread("t1", "stranger@x.com", 1)]})
    assert out == {"actions": [{"thread_id": "t1", "add": ["SS/Step-1"]}], "unmatched": ["t1"]}
