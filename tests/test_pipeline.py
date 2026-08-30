"""Unit tests. Fakes only: no file on disk, no network, no real trade."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import metrics
from src.kcex import cross_check
from src.realized import daily_net, fees_by_period, realized_events
from src.roundtrip import build_round_trips
from src.schema import AnnotatedTrade, Fill, RiskAnnotation, Role, RoundTrip, Side

T0 = datetime(2025, 6, 2, 12, 0, tzinfo=timezone.utc)
D = Decimal


def fill(mins, action, side=Side.LONG, qty="1", price="100000", fee="10", pnl="0",
         role=Role.TAKER, source="fake"):
    return Fill(ts=T0 + timedelta(minutes=mins), symbol="BTCUSDT", action=action,
                side=side, qty=D(qty), price=D(price), fee_usdt=D(fee),
                closing_pnl_usdt=D(pnl), role=role, source=source)


class TestFill:
    def test_naive_timestamp_is_rejected(self):
        with pytest.raises(ValueError, match="tz-aware"):
            Fill(ts=datetime(2025, 6, 2, 12, 0), symbol="BTCUSDT", action="open",
                 side=Side.LONG, qty=D(1), price=D(1), fee_usdt=D(0),
                 closing_pnl_usdt=D(0), role=Role.TAKER, source="fake")

    def test_non_utc_timestamp_is_rejected(self):
        with pytest.raises(ValueError, match="UTC"):
            Fill(ts=datetime(2025, 6, 2, 12, 0, tzinfo=timezone(timedelta(hours=4))),
                 symbol="BTCUSDT", action="open", side=Side.LONG, qty=D(1),
                 price=D(1), fee_usdt=D(0), closing_pnl_usdt=D(0),
                 role=Role.TAKER, source="fake")


class TestRoundTrips:
    def test_open_then_close_is_one_trip(self):
        trips, warns = build_round_trips([fill(0, "open"), fill(30, "close", pnl="500")])
        assert len(trips) == 1 and not warns
        assert trips[0].gross_pnl_usdt == D(500)
        assert trips[0].fees_usdt == D(20)          # both legs
        assert trips[0].net_pnl_usdt == D(480)
        assert trips[0].hold_seconds == 1800

    def test_scale_in_stays_one_trip(self):
        trips, _ = build_round_trips([
            fill(0, "open", qty="1"), fill(5, "open", qty="2"),
            fill(10, "close", qty="3", pnl="300"),
        ])
        assert len(trips) == 1
        assert trips[0].qty == D(3) and trips[0].n_entry_fills == 2

    def test_residual_blocks_the_trip_and_is_reported(self):
        """The real defect in the KCEX data: a dust long never closes, so the
        book never returns to flat and no trip can be emitted."""
        trips, warns = build_round_trips([
            fill(0, "open", qty="1"), fill(10, "close", qty="0.9", pnl="100"),
        ])
        assert trips == []
        assert any("still open" in w for w in warns)

    def test_close_with_no_open_is_warned_not_dropped(self):
        trips, warns = build_round_trips([fill(0, "close", qty="1", pnl="50")])
        assert len(trips) == 1
        assert any("no open in window" in w for w in warns)

    def test_long_and_short_books_are_independent(self):
        trips, _ = build_round_trips([
            fill(0, "open", side=Side.LONG), fill(1, "open", side=Side.SHORT),
            fill(2, "close", side=Side.SHORT, pnl="10"),
            fill(3, "close", side=Side.LONG, pnl="20"),
        ])
        assert {t.side for t in trips} == {Side.LONG, Side.SHORT}


class TestRealized:
    def test_only_closing_fills_become_events(self):
        ev = realized_events([fill(0, "open"), fill(1, "close", pnl="5"),
                              fill(2, "open"), fill(3, "close", pnl="-2")])
        assert len(ev) == 2
        assert [float(e.gross_pnl_usdt) for e in ev] == [5.0, -2.0]

    def test_fees_by_period_counts_entry_fees_too(self):
        fees = fees_by_period([fill(0, "open", fee="7"), fill(1, "close", fee="3")])
        assert fees["2025-06"] == D(10)

    def test_daily_net_subtracts_every_fee_paid_that_day(self):
        d = daily_net([fill(0, "open", fee="10"), fill(1, "close", fee="10", pnl="100")])
        assert d == [(T0.date(), 80.0)]


class TestCrossCheck:
    def test_identical_exports_match_fully(self):
        base = [fill(0, "open"), fill(1, "close", pnl="5")]
        assert cross_check(base, list(base)) == (2, 2, 0)

    def test_same_second_split_order_is_not_a_duplicate(self):
        """Collapsing on (ts, action, side, qty, price) deleted 11 real fills
        the first time this was written."""
        base = [fill(0, "open"), fill(0, "open")]
        assert cross_check(base, list(base)) == (2, 2, 0)

    def test_a_row_the_base_lacks_is_reported_unmatched(self):
        assert cross_check([fill(0, "open")], [fill(0, "open"), fill(1, "open")])[2] == 1


class TestMetrics:
    def _events(self):
        return realized_events([fill(0, "close", pnl="300"), fill(1, "close", pnl="-100"),
                                fill(2, "close", pnl="-100"), fill(3, "close", pnl="-100")])

    def test_summary_shape(self):
        s = metrics.summarize_realized(self._events(), total_fees_usdt=40.0)
        assert s.n_closes == 4
        assert s.win_rate == 0.25
        assert s.gross_usdt == 0.0
        assert s.net_usdt == -40.0
        assert s.profit_factor == 1.0
        assert s.cost_drag == pytest.approx(40 / 300)

    def test_max_drawdown_finds_peak_and_trough(self):
        curve = [(datetime(2025, 6, d, tzinfo=timezone.utc).date(), v)
                 for d, v in [(1, 0), (2, 100), (3, 40), (4, 120)]]
        dd = metrics.max_drawdown(curve)
        assert dd.max_dd_usdt == 60
        assert dd.trough_at.day == 3 and dd.recovered_at.day == 4

    def test_equity_curve_is_none_without_capital(self):
        """A percent return has no meaning without the equity it is a percent of."""
        assert metrics.equity_curve([(T0.date(), 100.0)], None) is None
        assert metrics.equity_curve([(T0.date(), 100.0)], 0) is None

    def test_equity_curve_indexes_to_100(self):
        (d, v), = metrics.equity_curve([(T0.date(), 100.0)], 1000.0)
        assert d == T0.date() and v == pytest.approx(110.0)


class TestRMultiple:
    def _trip(self, net):
        return RoundTrip(symbol="BTCUSDT", side=Side.LONG, opened_at=T0, closed_at=T0,
                         qty=D(1), avg_entry=D(1), avg_exit=D(1),
                         gross_pnl_usdt=D(net), fees_usdt=D(0), n_entry_fills=1,
                         n_exit_fills=1, maker_fills=0, taker_fills=2, source="fake")

    def test_r_is_none_without_planned_risk(self):
        """Better no R than an R computed off a guessed denominator."""
        assert AnnotatedTrade(trip=self._trip(300)).r_multiple is None
        assert AnnotatedTrade(trip=self._trip(300),
                              risk=RiskAnnotation(opened_at=T0)).r_multiple is None

    def test_r_uses_planned_risk_as_the_denominator(self):
        t = AnnotatedTrade(trip=self._trip(300),
                           risk=RiskAnnotation(opened_at=T0, planned_risk_usdt=D(100)))
        assert t.r_multiple == D(3)
