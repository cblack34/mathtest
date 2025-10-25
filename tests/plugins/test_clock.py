"""Smoke tests for the clock plugin."""

from mathtest.plugins.clock import ClockPlugin


def test_clock_plugin_generates_expected_problem() -> None:
    """Clock plugin should enforce 12-hour defaults and deterministic seeding."""

    plugin = ClockPlugin({"random-seed": 7})
    problem = plugin.generate_problem()

    assert problem.data["hour"] == 6
    assert problem.data["minute"] == 15
    assert problem.data["minute_interval"] == 15
    assert problem.data["accurate_hour"] is False
    assert problem.data["is_24_hour"] is False
    assert problem.data["answer"] == "6:15"
    assert problem.data["hour_hand_angle"] == 180.0
    assert problem.data["minute_hand_angle"] == 90.0
    assert "<svg" in problem.svg

    recreated = ClockPlugin.generate_from_data(problem.data)
    assert recreated.data == problem.data


def test_clock_plugin_supports_accurate_hour_and_24_hour_modes() -> None:
    """Clock plugin should adjust the hour hand and support 24-hour dials."""

    accurate = ClockPlugin(
        {
            "random-seed": 4,
            "minute-interval": 30,
            "accurate-hour": True,
        }
    )
    accurate_problem = accurate.generate_problem()

    assert accurate_problem.data["hour"] == 4
    assert accurate_problem.data["minute"] == 30
    assert accurate_problem.data["hour_hand_angle"] == 135.0

    military = ClockPlugin(
        {
            "random-seed": 11,
            "clock-24-hour": True,
            "minute-interval": 60,
        }
    )
    military_problem = military.generate_problem()

    assert military_problem.data["is_24_hour"] is True
    assert military_problem.data["hour"] == 14
    assert military_problem.data["minute"] == 0
    assert military_problem.data["answer"] == "14:00"
