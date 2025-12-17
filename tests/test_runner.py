import re

from biokit.runner import generate_run_id


def test_generate_run_id_format_and_uniqueness():
    run_id1 = generate_run_id()
    run_id2 = generate_run_id()
    pattern = re.compile(r"^\d{14}-[0-9a-f]{8}$")

    assert pattern.match(run_id1)
    assert pattern.match(run_id2)
    assert run_id1 != run_id2
