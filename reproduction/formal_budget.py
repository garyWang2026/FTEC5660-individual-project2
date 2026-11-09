"""Persistent worst-peak-price budget ledger with reservations before sending requests."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time


class ExperimentStop(BaseException):
    """Bypass upstream generic retry/fallback handlers on budget or integrity stops."""


def costs(prompt, output, cached=0):
    low = (max(0, prompt-cached) + cached*.02 + output*4) / 1_000_000
    return low, low*2


class BudgetLedger:
    def __init__(self, path, limit_cny=9.0):
        self.path = Path(path)
        self.limit_cny = limit_cny
        self.lock = threading.RLock()
        self.context = threading.local()
        self.events = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                event = json.loads(line)
                self.events[event['id']] = event

    def _append(self, event):
        with self.path.open('a') as f:
            f.write(json.dumps(event)+'\n')
            f.flush()
            os.fsync(f.fileno())
        self.events[event['id']] = dict(event)

    def committed(self):
        with self.lock:
            return sum(e['charged_upper_cny'] for e in self.events.values())

    def set_context(self, key, stage):
        self.context.key, self.context.stage = key, stage

    def wrap(self, create):
        def measured(**kwargs):
            if kwargs.get('stream'):
                raise ExperimentStop('Metered experiment requires non-streaming responses.')
            messages = kwargs['messages']
            output_cap = 4096
            # UTF-8 bytes plus generous chat-template overhead, deliberately not a reported token count.
            prompt_bound = sum(len(m['content'].encode('utf-8'))+256 for m in messages)+1024
            reserve = costs(prompt_bound, output_cap)[1]
            with self.lock:
                if self.committed()+reserve > self.limit_cny:
                    raise ExperimentStop('Budget reservation limit reached; completed work is saved.')
                event = {'id':len(self.events), 'key':getattr(self.context,'key','unknown'), 'stage':getattr(self.context,'stage','unknown'), 'state':'started', 'started_utc':datetime.now(timezone.utc).isoformat(), 'reserved_upper_cny':reserve, 'charged_upper_cny':reserve, 'prompt_bound':prompt_bound, 'output_cap':output_cap, 'request_model':kwargs['model'], 'temperature':kwargs.get('temperature'), 'prompt_sha256':hashlib.sha256(json.dumps(messages,sort_keys=True).encode()).hexdigest()}
                # A crash or response with unknown usage keeps the entire reservation charged.
                self._append(event)
            kwargs['max_tokens'] = output_cap
            start = time.perf_counter()
            try:
                response = create(**kwargs)
                if response.usage is None:
                    raise ExperimentStop('Response has no usage; stop rather than continue unmetered.')
                raw = response.usage.model_dump()
                prompt, output = raw['prompt_tokens'],raw['completion_tokens']
                cached = raw.get('prompt_cache_hit_tokens',(raw.get('prompt_tokens_details') or {}).get('cached_tokens',0)) or 0
                low, high = costs(prompt,output,cached)
                event.update({'state':'ok','prompt_tokens':prompt,'completion_tokens':output,'cached_input_tokens':cached,'total_tokens':prompt+output,'estimated_off_peak_cny':low,'charged_upper_cny':high,'response_model':response.model,'request_id':response.id,'finish_reason':response.choices[0].finish_reason})
                if prompt > prompt_bound or output > output_cap:
                    raise ExperimentStop('Usage exceeds preflight bound; stopped for inspection.')
                if response.choices[0].finish_reason != 'stop':
                    raise ExperimentStop('Truncated/unexpected completion; stopped for inspection.')
                return response
            except BaseException as exc:
                event['state'] = 'error'
                event['error_type'] = type(exc).__name__
                raise
            finally:
                event['duration_seconds'] = time.perf_counter()-start
                with self.lock:
                    self._append(event)
        return measured

    def summary(self, key=None):
        with self.lock:
            events = [e for e in self.events.values() if key is None or e['key']==key]
            return {'api_calls':len(events),'failed_or_unknown_api_calls':sum(e['state']!='ok' for e in events),'prompt_tokens':sum(e.get('prompt_tokens',0) for e in events),'completion_tokens':sum(e.get('completion_tokens',0) for e in events),'cached_input_tokens':sum(e.get('cached_input_tokens',0) for e in events),'total_tokens':sum(e.get('total_tokens',0) for e in events),'estimated_off_peak_cny':sum(e.get('estimated_off_peak_cny',0) for e in events),'charged_upper_cny':sum(e['charged_upper_cny'] for e in events),'unknown_reservations':sum(e['charged_upper_cny'] for e in events if 'total_tokens' not in e)}
