from orqelis_agent.platforms import linux, macos


def test_linux_does_not_claim_defender():
    assert linux.defender_status() == "n/a"


def test_macos_firewall_helper_exists():
    assert callable(macos.firewall_status)
    assert callable(macos.defender_status)
