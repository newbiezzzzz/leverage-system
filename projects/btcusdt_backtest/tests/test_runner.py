import csv, json, sys, tempfile, unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runner

def bars(closes):
    out=[]
    start=datetime(2026,1,5,3,0,tzinfo=timezone.utc)
    for i,c in enumerate(closes):
        out.append({"dt":start+timedelta(minutes=5*i),"open":float(c),"high":float(c)+1,"low":float(c)-1,"close":float(c),"volume":10.0})
    return out

def spec(**kw):
    s={"strategy_id":"test","version":1,"instrument":"BTCUSDT","market_type":"spot","timeframe_minutes":5,"direction":"long_only",
       "indicators":[{"id":"fast","type":"sma","period":2},{"id":"slow","type":"sma","period":3}],
       "entry":{"logic":"all","conditions":[{"left":{"indicator":"fast"},"operator":"crosses_above","right":{"indicator":"slow"}}]},
       "exit":{"mode":"stop_and_target","stop_points":2,"target_points":3},
       "position_sizing":{"mode":"fixed_quantity","quantity":0.001},
       "execution":{"signal_timing":"bar_close","entry_timing":"next_bar_open","intrabar_collision":"stop_first","allow_lookahead":False},
       "costs":{"fee_rate_per_side":0.001,"slippage_bps_per_side":10},
       "sessions":["00:00-23:59"]}
    s.update(kw);return s

class EngineTests(unittest.TestCase):
    def test_empty_csv_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.csv";p.write_text("timestamp,open,high,low,close,volume\n")
            with self.assertRaisesRegex(ValueError,"zero data rows"):runner.load_bars(p)
    def test_invalid_ohlc_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.csv";p.write_text("timestamp,open,high,low,close,volume\n2026-01-01T00:00:00+00:00,100,90,95,98,1\n")
            with self.assertRaisesRegex(ValueError,"Invalid OHLC"):runner.load_bars(p)
    def test_sma_is_causal(self):
        self.assertEqual(runner.sma([1,2,3,4],2),[None,1.5,2.5,3.5])
    def test_ema_seed_and_update(self):
        out=runner.ema([1,2,3,4],2)
        self.assertIsNone(out[0]);self.assertEqual(out[1],1.5);self.assertAlmostEqual(out[2],2.5)
    def test_cross_above(self):
        b=bars([4,3,2,3,5]);inds={"a":{"value":[4,3,2,3,5]},"b":{"value":[3,3,3,3,3]}}
        c={"left":{"indicator":"a"},"operator":"crosses_above","right":{"indicator":"b"}}
        self.assertFalse(runner.cond(c,3,b,inds));self.assertTrue(runner.cond(c,4,b,inds))
    def test_missing_costs_block(self):
        s=spec();s["costs"]["slippage_bps_per_side"]=None
        with self.assertRaisesRegex(ValueError,"fee-rate and slippage-bps"):runner.validate(s)
    def test_unsupported_indicator_fails(self):
        with self.assertRaisesRegex(ValueError,"Unsupported indicator"):runner.ind(bars([1,2,3]),{"id":"x","type":"made_up"})
    def test_stop_wins_when_stop_and_target_hit_same_bar(self):
        b=bars([100,100,100,100,100,100]);b[2]["high"]=104;b[2]["low"]=97
        s=spec(indicators=[],entry={"logic":"all","conditions":[{"left":{"price":"close"},"operator":"gte","right":{"constant":99}}]})
        t=runner.backtest(b,s)
        self.assertTrue(t)
        self.assertEqual(t[0]["exit_reason"],"stop")
    def test_next_bar_open_execution(self):
        b=bars([8,10,12,12,12,12])
        s=spec(indicators=[],entry={"logic":"all","conditions":[{"left":{"price":"close"},"operator":"gte","right":{"constant":10}}]})
        t=runner.backtest(b,s)
        self.assertEqual(t[0]["entry_price"],12.0)
        self.assertEqual(t[0]["entry_time"],b[2]["dt"].isoformat())
    def test_fees_and_slippage_are_reported(self):
        b=bars([10,10,12,12,12,12])
        s=spec(indicators=[],entry={"logic":"all","conditions":[{"left":{"price":"close"},"operator":"gte","right":{"constant":10}}]})
        t=runner.backtest(b,s)
        notional = (t[0]["entry_price"] + t[0]["exit_price"]) * 0.001
        self.assertAlmostEqual(t[0]["fees_usdt"], round(notional * 0.001, 6))
        self.assertAlmostEqual(t[0]["slippage_usdt"], round(notional * 10 / 10000, 6))
        self.assertAlmostEqual(t[0]["costs_usdt"], round(t[0]["fees_usdt"] + t[0]["slippage_usdt"], 6))
    def test_monthly_summary_and_drawdown(self):
        ts=[{"entry_time":"2026-01-02T00:00:00+00:00","exit_time":"2026-01-02T00:05:00+00:00","net_usdt":100,"gross_usdt":105,"fees_usdt":2,"slippage_usdt":3,"costs_usdt":5},
            {"entry_time":"2026-01-03T00:00:00+00:00","exit_time":"2026-01-03T00:05:00+00:00","net_usdt":-150,"gross_usdt":-145,"fees_usdt":2,"slippage_usdt":3,"costs_usdt":5}]
        self.assertEqual(runner.monthly(ts)[0]["net_usdt"],-50)
        sm=runner.summary(ts,1000);self.assertEqual(sm["max_drawdown_usdt"],150);self.assertEqual(sm["max_consecutive_losses"],1)
    def test_short_profit_direction(self):
        b=bars([100,100,100,95,95,95])
        s=spec(market_type="usdt_perpetual",direction="short_only",indicators=[],short_entry={"logic":"all","conditions":[{"left":{"price":"close"},"operator":"gte","right":{"constant":99}}]})
        t=runner.backtest(b,s)
        self.assertGreater(t[0]["gross_usdt"],0)
    def test_fractional_btc_quantity_supported(self):
        s=spec(position_sizing={"mode":"fixed_quantity","quantity":0.0015})
        self.assertAlmostEqual(runner.validate(s),0.0015)
    def test_market_type_required(self):
        s=spec();s.pop("market_type")
        with self.assertRaisesRegex(ValueError,"market_type"):runner.validate(s)
    def test_nonconservative_collision_policy_blocked(self):
        s=spec();s["execution"]["intrabar_collision"]="target_first"
        with self.assertRaisesRegex(ValueError,"stop-first"):runner.validate(s)
    def test_lookahead_prohibited(self):
        s=spec(execution={"signal_timing":"bar_close","entry_timing":"next_bar_open","allow_lookahead":True})
        with self.assertRaisesRegex(ValueError,"Look-ahead"):runner.validate(s)

if __name__=="__main__":unittest.main()
