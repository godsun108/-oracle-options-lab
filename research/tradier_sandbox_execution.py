"""Explicit sandbox-only paper orders. No production host or automatic strategy selection.

Sources: https://docs.tradier.com/brokerage-api/trading and /docs/orders.
Journal claims are persisted before submission; uncertain submissions never retry.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE='https://sandbox.tradier.com/v1'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('redirect refused')

class Sandbox:
    def __init__(self,token,account,*,transport=None):
        if not token or not re.fullmatch(r'[A-Za-z0-9]{4,16}',account or ''):
            raise ValueError('separate sandbox credentials required')
        self.token=token;self.account=account;self.transport=transport or urllib.request.build_opener(NoRedirect()).open

    def request(self,path,data=None):
        if not path.startswith('/'):raise ValueError('invalid path')
        body=urllib.parse.urlencode(data).encode() if data is not None else None
        req=urllib.request.Request(BASE+path,data=body,headers={'Authorization':'Bearer '+self.token,
                    'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'})
        with self.transport(req,timeout=25) as response:return json.load(response)

    def preflight(self):
        accounts=self.request('/user/profile')['profile']['account']
        if isinstance(accounts,dict):accounts=[accounts]
        if not any(a.get('account_number')==self.account for a in accounts):raise ValueError('sandbox account mismatch')
        return {'status':'SANDBOX_ACCOUNT_VERIFIED','environment':'sandbox','orders_enabled':False,
                'paper_submission_enabled':False,'broker_fills_verified':False}

    def payload(self,intent):
        if intent.get('environment')!='sandbox' or intent.get('quantity')!=1 or type(intent.get('quantity')) is not int:
            raise ValueError('one-contract sandbox intent required')
        symbol=intent.get('option_symbol','');side=intent.get('side');price=intent.get('limit_price')
        if not re.fullmatch(r'SPY\d{6}[CP]\d{8}',symbol) or side not in ('buy_to_open','sell_to_close'):
            raise ValueError('only long SPY options supported')
        if type(price) not in (int,float) or not math.isfinite(price) or not 0<price<=20 or round(price,2)!=price:
            raise ValueError('finite cent limit at most $2000 per contract required')
        return {'class':'option','symbol':'SPY','option_symbol':symbol,'side':side,'quantity':'1',
                'type':'limit','duration':'day','price':format(price,'.2f')}

    def submit(self,intent,journal_path,*,paper_enabled=False):
        if paper_enabled is not True:raise ValueError('explicit sandbox submission opt-in required')
        payload=self.payload(intent)
        key=intent.get('intent_id','')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,48}',key):raise ValueError('stable intent_id required')
        digest=hashlib.sha256(json.dumps(intent,sort_keys=True,allow_nan=False).encode()).hexdigest()
        path=Path(journal_path);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('a+') as f:
            fcntl.flock(f,fcntl.LOCK_EX);f.seek(0)
            entries=[json.loads(line) for line in f if line.strip()]
            if any(e['intent_id']==key for e in entries):raise ValueError('intent already claimed; reconcile before any further action')
            self.preflight()
            if payload['side']=='sell_to_close':
                positions=self.request('/accounts/'+self.account+'/positions').get('positions') or {}
                rows=positions.get('position') or []
                if isinstance(rows,dict):rows=[rows]
                if sum(float(p['quantity']) for p in rows if p.get('symbol')==payload['option_symbol'])<1:
                    raise ValueError('no sandbox long position to close')
            payload['tag']='oq-'+key
            preview=self.request('/accounts/'+self.account+'/orders',{**payload,'preview':'true'})
            if preview.get('errors') or preview.get('order',{}).get('result') is not True:
                raise ValueError('broker preview did not explicitly pass')
            def append(record):
                f.seek(0,2);f.write(json.dumps(record,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
            claim={'intent_id':key,'intent_sha256':digest,'tag':payload['tag'],'state':'SUBMISSION_UNCERTAIN',
                   'timestamp':datetime.now(timezone.utc).isoformat(),'environment':'sandbox','orders_enabled':False}
            append(claim)
            result=self.request('/accounts/'+self.account+'/orders',{**payload,'preview':'false'})
            order=result.get('order',{});oid=order.get('id')
            if order.get('status')!='ok' or type(oid) is not int or oid<=0:
                raise ValueError('submission uncertain; inspect sandbox orders by tag')
            accepted={**claim,'state':'ACKNOWLEDGED_NOT_FILLED','order_id':oid}
            append(accepted)
            return accepted

    def reconcile(self,order_id,intent):
        payload=self.payload(intent)
        if type(order_id) is not int or order_id<=0:raise ValueError('invalid order id')
        raw=self.request('/accounts/'+self.account+'/orders/'+str(order_id))['order']
        for field in ('option_symbol','side','type','duration'):
            if raw.get(field)!=payload[field]:raise ValueError('broker order identity mismatch')
        if raw.get('id')!=order_id or raw.get('tag')!='oq-'+intent['intent_id']:raise ValueError('broker order tag mismatch')
        qty=raw.get('exec_quantity',0);price=raw.get('avg_fill_price',0)
        if any(type(v) not in (int,float) or not math.isfinite(v) for v in (qty,price)):
            raise ValueError('invalid broker fill')
        if not 0<=qty<=1 or price<0 or raw.get('quantity')!=1:raise ValueError('invalid broker quantity')
        filled=raw.get('status')=='filled' and qty==1 and price>0
        if filled and ((payload['side']=='buy_to_open' and price>float(payload['price'])) or
                       (payload['side']=='sell_to_close' and price<float(payload['price']))):
            raise ValueError('fill violates limit')
        return {'schema':'oracle-sandbox-fill-v1','order_id':order_id,'status':raw.get('status'),
                'executed_quantity':qty,'average_fill_price':price,'broker_paper_fill_verified':filled,
                'broker_fills_verified':False,'live_fill_verified':False,'orders_enabled':False,
                'environment':'sandbox','retrieved_at':datetime.now(timezone.utc).isoformat(),
                'response_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True,allow_nan=False).encode()).hexdigest(),
                'note':'Broker sandbox simulation; not exchange execution or settled PnL.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    p.add_argument('--intent');p.add_argument('--journal');p.add_argument('--submit-paper',action='store_true')
    p.add_argument('--order-id',type=int);a=p.parse_args()
    if a.submit_paper and (not a.intent or not a.journal or a.order_id):p.error('submission requires intent and durable journal; no order-id')
    if a.order_id and (not a.intent or a.submit_paper):p.error('reconciliation requires intent; cannot also submit')
    if a.intent and not (a.submit_paper or a.order_id):p.error('choose submit-paper or order-id')
    token=os.getenv('TRADIER_SANDBOX_TOKEN','');account=os.getenv('TRADIER_SANDBOX_ACCOUNT_ID','')
    result={'status':'SANDBOX_CREDENTIALS_MISSING','orders_enabled':False,'paper_submission_enabled':False,
            'broker_fills_verified':False,'environment':'sandbox'}
    if token and account:
        try:
            client=Sandbox(token,account)
            if a.submit_paper:
                result=client.submit(json.loads(Path(a.intent).read_text()),a.journal,paper_enabled=True)
            elif a.order_id:
                client.preflight()
                result=client.reconcile(a.order_id,json.loads(Path(a.intent).read_text()))
            else:result=client.preflight()
        except (KeyError,ValueError,TypeError,OSError) as e:
            result.update(status='SANDBOX_OPERATION_FAILED',error_type=type(e).__name__)
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print('Sandbox operation:',result.get('status',result.get('state')))
    if result.get('status') in ('SANDBOX_OPERATION_FAILED','SANDBOX_CREDENTIALS_MISSING') and (a.submit_paper or a.order_id):raise SystemExit(1)
if __name__=='__main__':main()
