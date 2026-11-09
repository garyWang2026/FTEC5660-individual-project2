import json
from types import SimpleNamespace
import pytest
from reproduction.formal_budget import BudgetLedger, ExperimentStop
from reproduction.formal_metrics import locomo_f1, token_f1


def response():
    usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':40})
    return SimpleNamespace(usage=usage,model='fake',id='fake',choices=[SimpleNamespace(finish_reason='stop')])


def test_reservation_survives_restart_and_prevents_another_charge(tmp_path):
    path=tmp_path/'ledger.jsonl'
    meter=BudgetLedger(path,limit_cny=.04)
    def timeout(**kw):raise TimeoutError('simulation')
    with pytest.raises(TimeoutError):
        meter.wrap(timeout)(model='fake',messages=[{'role':'user','content':'x'}])
    resumed=BudgetLedger(path,limit_cny=.04)
    assert resumed.committed()>0
    with pytest.raises(ExperimentStop):
        resumed.wrap(lambda **kw:pytest.fail('must not send another paid request'))(model='fake',messages=[{'role':'user','content':'x'}])


def test_success_releases_unused_reservation_and_jsonl_is_durable(tmp_path):
    path=tmp_path/'ledger.jsonl'
    meter=BudgetLedger(path)
    meter.set_context('trial:arm:question','retrieval')
    meter.wrap(lambda **kw:response())(model='fake',messages=[{'role':'user','content':'x'}])
    resumed=BudgetLedger(path)
    assert resumed.summary()['api_calls']==1
    assert resumed.summary()['prompt_tokens']==100
    assert resumed.summary()['charged_upper_cny']==pytest.approx((60*2+40*.04+20*8)/1e6)
    assert len(path.read_text().splitlines())==2


def test_missing_usage_keeps_reservation_and_stops(tmp_path):
    meter=BudgetLedger(tmp_path/'ledger.jsonl')
    with pytest.raises(ExperimentStop):
        meter.wrap(lambda **kw:SimpleNamespace(usage=None))(model='fake',messages=[{'role':'user','content':'x'}])
    assert meter.summary()['unknown_reservations']>0


def test_official_scoring_category_rules_and_multiset_counts():
    assert token_f1('cat cat','cat')==pytest.approx(2/3)
    assert locomo_f1('red, blue','blue, red',1)==1
    assert locomo_f1('No','No; detailed explanation',3)==1
    assert locomo_f1('The counselors','a counselor',4)==1
    assert locomo_f1('No','No; detailed explanation',4)<1
