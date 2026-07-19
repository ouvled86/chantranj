from app.services.elo import delta, expected_score, k_factor


def test_expected_score_symmetry() -> None:
    assert abs(expected_score(1200, 1200) - 0.5) < 1e-9
    assert expected_score(1400, 1200) + expected_score(1200, 1400) == 1.0
    assert expected_score(1600, 1200) > 0.9


def test_k_factor_provisional() -> None:
    assert k_factor(0) == 40
    assert k_factor(29) == 40
    assert k_factor(30) == 20


def test_delta_values() -> None:
    # Equal ratings, provisional win: +20
    assert delta(1200, 1200, 1.0, 0) == 20
    # Equal ratings, established draw: 0
    assert delta(1200, 1200, 0.5, 100) == 0
    # Upset win pays more
    assert delta(1200, 1400, 1.0, 100) > delta(1400, 1200, 1.0, 100)
