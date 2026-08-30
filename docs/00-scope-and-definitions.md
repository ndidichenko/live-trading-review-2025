# 00. Scope and definitions

> Every quantity in this repo is defined once, here. If a number appears
> elsewhere without a definition on this page, it is a bug.

## Purpose

To show a real example of trading strategies, managing risk, doing the research
and committing to the process, in order to outperform the asset I accumulate,
which in my case is BTC.

2025 is the first year I properly logged my trades and process.

## Window

Two records cover two windows, and the difference matters:

| | Window (UTC) | Source | What it can tell you |
|---|---|---|---|
| **Documented book** | 2025-03-09 to 2025-12-30 | manual trade log | trades, R, risk, sleeve |
| **Venue-verified** | 2025-06-02 to 2025-12-30 | KCEX export | fills, prices, fees, realized PnL |

- Manual log only, no venue export: **2025-03-09 to 2025-06-01**. This is the
  sizing ramp, from $1 of risk per trade upward, on a different venue and at a
  size where the PnL is immaterial. What matters in those months is the trades
  and the risk management, not the money.
- Screenshot only, outside this repo's scope: 2025-11-09 to 2026-02-06 and
  2026-03-01 to 2026-05-16.
- Last trade on the venue: 2026-05-16.

## Venue, instrument, account

- KCEX, BTC/USDT perpetual, cross margin. 3 ETH and 3 SOL fills in the window,
  ignored.
- Personal capital. Not a fund, not client money, not a signal service.

KCEX offers the lowest commissions in the crypto exchange space, which matters a
great deal for most of my day-trading strategies. On a tier-1 venue like Binance,
fees at my tier would eat at least third of the net profit.

Every venue carries its own custody risk. That is the main reason I hold no more
than 30% of my whole portfolio on an exchange. The FTX collapse in 2022, and the
millions in frozen or lost funds, is the example.

## Definitions

| Term | Definition used here |
|---|---|
| **Trade** | One position, as recorded in the manual log. 382 in the documented book |
| **Closing fill** | One venue-reported position reduction, carrying the venue's own `Closing PNL`. 391 in the venue window. One trade can close in several fills, and one fill can close two trades, which is why the two counts differ |
| **Gross PnL** | Sum of venue `Closing PNL`. Before fees |
| **Fees** | Entry and exit fees, both legs, as charged. Always a cost. Funding is included |
| **Net PnL** | Gross minus all fees in the period. Exact at period level, approximate per trade, because an entry fee belongs to a position rather than to one closing fill |
| **1R** | The USD amount lost if the stop is hit: stop distance times position size. Sized at 1% to 2% of total capital. Median across 2025 was **1.21%**, the largest single trade **1.89%**, and no trade exceeded 2% |
| **Starting capital** | 15,000 USDT |
| **Compounding** | Size recomputed on a 10% change in equity, measured on the whole 15k portfolio rather than the exchange balance |
| **Drawdown, %** | Peak to trough on the equity index. **-29.0% on 2025-08-06** |
| **Drawdown, USDT** | Peak to trough on cumulative net. **-6,231, 2025-11-04 to 2025-12-22, not recovered in window** |

The two drawdowns are different events. The deepest percentage drawdown is early,
on small equity. The largest dollar drawdown is late, on larger equity, and was
still open when the data ends. Both are stated because quoting one without naming
which it is would be misleading.

## Timezone

The KCEX export carries no timezone, and two exports of this account are shifted
3h against each other. Both were resolved against BTCUSDT 1-minute candles: the
2025-11 export stamps **UTC+1**, the 2026-05 export **UTC+4**. After normalising
to UTC they agree on **390 of 390** overlapping fills. The manual log stamps
UTC+0, established the same way.

Everything in this repo is UTC. Reproduce with `scripts/verify_timezone.py`.

## Benchmark

In 2025 I mostly traded BTC, and I treat BTC as an asset in the same way as the
S&P 500 or gold. My long-term investments are in BTC, so BTC is my personal
benchmark, and every strategy I trade live is designed to outperform it. If the
majority of my portfolio were in the S&P or gold, that would be the benchmark
instead.

Series: **Binance BTCUSDT spot, daily close.**

- Over the venue window, 2025-06-02 to 2025-12-30: **-16%**
- Over calendar 2025, 2024-12-31 close to 2026-01-02 close: **-3.83%**

The window-matched figure is the honest comparison, because it is the period in
which the book was actually running.

## What this is not

- Not a backtest. Every fill is money that moved.
- Not a strategy description. Entry and exit rules are deliberately absent.
- Not a track record you can invest in.
