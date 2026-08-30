# 03. Costs and execution

## The cost stack, measured

| | |
|---|---|
| Gross realized | +7,571.70 USDT |
| Fees, entry and exit | -1,578.36 USDT |
| **Fees as % of gross profit** | **3.3%** |
| Net | +5,993.34 USDT |
| Maker share of fills | **30%** |

Retail tier, no VIP. Maker fills are deliberate because some strategies and entries
require limit entries, exits or both.

One number worth keeping in view, the median stop
is **0.47% of entry price**, and round-trip taker cost is roughly **12bp**. Costs
are therefore about a quarter of 1R before any slippage. That ratio, not the
headline fee percentage, is what constrains the book. See Capacity in the README.

## Funding

PnL is calculated net of fees, and funding is included and accounted for in that
figure.

## Slippage

Intended price is the candle open at the time of each signal, on the timeframe the
strategy trades. Slippage could be computed from intended versus filled price, and
it is not computed here.

Two reasons, one good and one to be honest about. The good one: at a median
notional of 31,000 USDT on BTC perpetual, position size is far too small to raise
a liquidity concern, so market impact is not the issue. The honest one: with
manual execution the gap between signal and fill is not market impact, it is reaction time, and that gap is not currently logged. Against a 47bp stop it does not take
much of it to matter, so this is a measurement gap rather than a proven non-issue,
and closing it is part of the 2026 automation work below.

## Execution notes

One of my main objectives for 2026 is to automate execution of the majority of the
strategies. That saves time and improves execution quality (no missed trades,
faster calculation and execution, better prices).

The main constraint is automating market structure the exact way I interpret it,
which is what full automation requires. Partial automation is already possible,
with some price levels still marked manually and fed to the engine.

The second constraint is that KCEX has no API for automated execution, and moving
to Binance or Bybit would raise trading costs noticeably unless the account
reaches a higher VIP tier (Level 3+), which needs a bigger portfolio. Cost and automation
pull against each other here, and that is unresolved.

## Venue

No venue issues, outages or delays were encountered throughout the live window.
