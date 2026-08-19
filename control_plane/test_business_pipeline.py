import unittest
from control_plane.opportunity_engine import score_opportunity, rank_opportunities, build_business_pipeline
from control_plane.business_pipeline import new_pipeline, can_advance, advance

class BusinessPipelineTests(unittest.TestCase):
    def candidate(self):
        return {"id":"opp-1","problem":"repetitive business task","customer":"SMEs","offer":"automation service","evidence":["validated interviews"],"first_revenue_speed":90,"zero_cost_feasibility":95,"demand_evidence":85,"automation_potential":90,"profit_margin":80,"competition":60,"scalability":75,"owner_capability_fit":90}
    def test_evidence_based_score(self):
        result=score_opportunity(self.candidate())
        self.assertGreaterEqual(result.score,75)
        self.assertEqual(result.decision,"candidate")
    def test_missing_evidence_cannot_be_candidate(self):
        result=score_opportunity({"id":"opp-2","first_revenue_speed":100})
        self.assertEqual(result.decision,"needs-evidence")
        self.assertTrue(result.missing_evidence)
    def test_rank_orders_by_score(self):
        low={"id":"low","problem":"p","customer":"c","offer":"o","evidence":["e"],"first_revenue_speed":10}
        high=self.candidate()
        self.assertEqual(rank_opportunities([low,high])[0]["id"],"opp-1")
    def test_pipeline_starts_at_validation(self):
        pipeline=build_business_pipeline(self.candidate())
        self.assertEqual(pipeline["status"],"awaiting_owner_approval")
        self.assertEqual(pipeline["stages"][0]["status"],"ready")
        self.assertTrue(pipeline["safety"]["no_live_money_movement"])
    def test_gated_transition_requires_approval(self):
        pipeline=new_pipeline("opp-1")
        pipeline=advance(pipeline,"customer_discovery",set()) if False else pipeline
        result=can_advance(pipeline,"customer_discovery",set())
        self.assertFalse(result.ok)
        self.assertIn("approval required",result.reason)
        self.assertTrue(can_advance(pipeline,"customer_discovery",{"customer_discovery"}).ok)
    def test_cannot_skip_stage(self):
        pipeline=new_pipeline("opp-1")
        result=can_advance(pipeline,"build",{"build"})
        self.assertFalse(result.ok)

if __name__ == "__main__": unittest.main()
