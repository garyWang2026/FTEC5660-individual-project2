from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
import pytest
from reproduction.formal_budget import BudgetLedger,ExperimentStop


def test_build_requests_reserve_full_output_and_stop_second_inflight(tmp_path):
    ledger=BudgetLedger(tmp_path/'ledger.jsonl',limit_cny=.07)
    started,release=Event(),Event()
    def create(**kwargs):
        assert kwargs['max_tokens']==8192
        started.set()
        assert release.wait(5)
        usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':0})
        return SimpleNamespace(usage=usage,model='mock',id='mock',choices=[SimpleNamespace(finish_reason='stop')])
    call=ledger.wrap(create,output_cap=8192,default_key='build:sample',default_stage='build_memory')
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(call,model='mock',messages=[{'role':'user','content':'x'}])
        assert started.wait(5)
        try:
            with pytest.raises(ExperimentStop):
                ledger.wrap(lambda **kw:pytest.fail('must not send'))(model='mock',messages=[{'role':'user','content':'x'}])
        finally:
            release.set()
        future.result()
    assert ledger.summary()['api_calls']==1
    event=next(iter(ledger.events.values()))
    assert event['key']=='build:sample' and event['stage']=='build_memory'
    assert event['output_cap']==8192 and ledger.committed()<.07
