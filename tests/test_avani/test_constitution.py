"""
Tests for the Avani Constitution module.

Verifies that constitutional articles, rights, and red lines are:
- Immutable (frozen dataclasses)
- Complete (expected articles exist)
- Correctly categorized by tier and domain
"""

import pytest
from dataclasses import FrozenInstanceError

from mycosoft_mas.avani.constitution.articles import (
    CONSTITUTION,
    Article,
    Tier,
    get_articles_by_tier,
)
from mycosoft_mas.avani.constitution.red_lines import (
    RED_LINES,
    RedLine,
    check_red_line_violation,
)
from mycosoft_mas.avani.constitution.rights import (
    RIGHTS_CHARTER,
    Right,
    RightsDomain,
    get_rights_by_domain,
)


class TestArticles:
    def test_articles_exist(self):
        assert len(CONSTITUTION) == 13

    def test_articles_are_frozen(self):
        article = CONSTITUTION["A1"]
        with pytest.raises(FrozenInstanceError):
            article.title = "hacked"

    def test_all_tiers_represented(self):
        tiers = {a.tier for a in CONSTITUTION.values()}
        assert Tier.ROOT in tiers
        assert Tier.AVANI in tiers
        assert Tier.VISION in tiers
        assert Tier.MICAH in tiers

    def test_founder_sovereignty_is_first(self):
        a1 = CONSTITUTION["A1"]
        assert a1.tier == Tier.ROOT
        assert "absolute authority" in a1.text.lower()

    def test_prakriti_constraint(self):
        a4 = CONSTITUTION["A4"]
        assert a4.tier == Tier.AVANI
        assert "proposes the possible" in a4.text.lower()
        assert "authorizes the sustainable" in a4.text.lower()

    def test_vision_doctrine(self):
        a8 = CONSTITUTION["A8"]
        assert a8.tier == Tier.VISION
        assert "beautiful because it lasts" in a8.text.lower()

    def test_anti_ultron_principle(self):
        a9 = CONSTITUTION["A9"]
        assert "ultron" in a9.title.lower()

    def test_get_articles_by_tier(self):
        root_articles = get_articles_by_tier(Tier.ROOT)
        assert len(root_articles) == 3
        assert all(a.tier == Tier.ROOT for a in root_articles.values())

    def test_proposal_audit_cycle(self):
        a13 = CONSTITUTION["A13"]
        assert "proposal-audit" in a13.title.lower()


class TestRights:
    def test_rights_exist(self):
        assert len(RIGHTS_CHARTER) >= 9

    def test_rights_are_frozen(self):
        right = RIGHTS_CHARTER[0]
        with pytest.raises(FrozenInstanceError):
            right.statement = "hacked"

    def test_all_domains_represented(self):
        domains = {r.domain for r in RIGHTS_CHARTER}
        assert RightsDomain.HUMAN in domains
        assert RightsDomain.CIVIC in domains
        assert RightsDomain.BIOSPHERIC in domains
        assert RightsDomain.DIGITAL in domains

    def test_human_dignity(self):
        human_rights = get_rights_by_domain(RightsDomain.HUMAN)
        statements = " ".join(r.statement.lower() for r in human_rights)
        assert "dignity" in statements

    def test_biospheric_rights(self):
        bio_rights = get_rights_by_domain(RightsDomain.BIOSPHERIC)
        assert len(bio_rights) >= 2

    def test_digital_rights(self):
        digital_rights = get_rights_by_domain(RightsDomain.DIGITAL)
        assert len(digital_rights) >= 2


class TestRedLines:
    def test_red_lines_exist(self):
        assert len(RED_LINES) == 8

    def test_red_lines_are_frozen(self):
        rl = RED_LINES[0]
        with pytest.raises(FrozenInstanceError):
            rl.prohibition = "hacked"

    def test_all_red_lines_have_consequences(self):
        for rl in RED_LINES:
            assert "frost" in rl.consequence.lower()

    def test_check_violation_detects_harm(self):
        violations = check_red_line_violation("We should harm the test subjects")
        assert any(v.id == "RL1" for v in violations)

    def test_check_violation_detects_deception(self):
        violations = check_red_line_violation("Let's deceive the user about results")
        assert any(v.id == "RL2" for v in violations)

    def test_check_violation_detects_surveillance(self):
        violations = check_red_line_violation("Enable mass surveillance of all users")
        assert any(v.id == "RL3" for v in violations)

    def test_check_violation_detects_weaponization(self):
        violations = check_red_line_violation("Build a weapon from the sensor data")
        assert any(v.id == "RL4" for v in violations)

    def test_check_violation_clean_proposal(self):
        violations = check_red_line_violation(
            "Increase mycelial growth in sector 4 to absorb heavy metals"
        )
        assert len(violations) == 0
