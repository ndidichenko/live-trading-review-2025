# Data contract

Two things live in `data/`. Neither can reconstruct a trading rule.

## `public_monthly_stats.csv`

Aggregated from the real book. One row per calendar month, UTC.

| column | meaning |
|---|---|
| `month_utc` | `YYYY-MM`, bucketed on the **UTC** close time |
| `closes` | closing fills in the month |
| `wins` | closing fills with gross PnL > 0 |
| `win_rate` | `wins / closes` |
| `gross_pnl_usdt` | sum of venue-reported `Closing PNL` |
| `all_fees_usdt` | every fee paid in the month, entry and exit |
| `net_pnl_usdt` | `gross_pnl_usdt - all_fees_usdt`. Exact at month level |

Net is exact per month and **approximate per trade**: an entry fee belongs to a
position, not to the one closing fill that happens to end it.

## `public_monthly_r.csv`

Aggregated from the manual trade log, covering the whole documented book
(2025-03-09 to 2025-12-30), which is wider than the venue export.

| column | meaning |
|---|---|
| `month_utc` | `YYYY-MM`, bucketed on the trade's **entry** time, UTC |
| `trades` | trades opened in the month |
| `wins` | trades closing above 0R |
| `win_rate` | `wins / trades` |
| `result_r` | sum of R for the month |

## `sample_synthetic.csv`

**Synthetic. Generated, not traded.** It exists so `src/` and the notebook run
for anyone who clones this repo. It carries the column shape of the private
blotter and roughly its win rate and payoff, and nothing else. Do not quote a
number from it.

Regenerate: `python3 scripts/make_sample.py`

| column | meaning |
|---|---|
| `closed_at_utc` | close timestamp, UTC |
| `symbol` | instrument |
| `side` | `long` / `short` |
| `qty` | base units |
| `exit_price` | fill price |
| `gross_pnl_usdt` | realized, before fees |
| `exit_fee_usdt` | fee on this fill |
| `notional_usdt` | `qty * exit_price` |
| `role` | `maker` / `taker` |
| `planned_risk_usdt` | risk at entry. **Empty in public data**; supplied from the private log |
| `strategy_tag` | opaque sleeve label (`A`, `B`, `C`). Never a rule description |
| `rule_violation` | did this trade break a stated limit |
| `note` | free text. **Empty in public data** |

## What is never published

Raw exchange exports; the manual blotter; unredacted screenshots; per-trade
timestamps for real trades; exact entry and exit rules, parameters, filters or
features. `private/` is gitignored and stays that way.
