"""Independent local audit. Run: python audit.py --repo PATH --deps PATH --out PATH."""
import argparse, sys, json, random, time, hashlib, platform
from pathlib import Path
from collections import Counter

cli = argparse.ArgumentParser()
cli.add_argument('--repo', required=True)
cli.add_argument('--deps', required=True)
cli.add_argument('--out', required=True)
args = cli.parse_args()
sys.path[:0] = [str(Path(args.deps).resolve()), str(Path(args.repo).resolve())]
from backend.api.services import calculate, CalculationError
from backend.api.schemas import CalculateRequest
from backend.api.main import app
from backend.engine import fields
from fastapi.testclient import TestClient

TAPS = {163:(7,6,3,0),233:(74,0),239:(158,0),283:(12,7,5,0),409:(87,0),571:(10,5,2,0)}
SEED = 20261125
rng = random.Random(SEED)

# Reference uses MSB-first Horner reduction, not the project's leading-term loop.
def rem(a, p):
    m = p.bit_length()-1
    r = 0
    for k in range(a.bit_length()-1, -1, -1):
        r = (r << 1) | ((a >> k) & 1)
        if r >> m: r ^= p
    return r

def product(a,b):
    z = 0
    while b:
        low = b & -b
        z ^= a << (low.bit_length()-1)
        b ^= low
    return z

def mul(a,b,p): return rem(product(a,b),p)

# Binary almost-inverse: degree swaps and single cancellations; no quotient EEA.
def inv(a,p):
    u,v,g,h = rem(a,p),p,1,0
    if not u: raise ZeroDivisionError()
    while u != 1:
        d = u.bit_length()-v.bit_length()
        if d < 0: u,v,g,h,d = v,u,h,g,-d
        u ^= v << d
        g ^= h << d
        if not u: raise ZeroDivisionError()
    return rem(g,p)

def power(a,n,p):
    z=1
    while n:
        if n&1: z=mul(z,a,p)
        a=mul(a,a,p); n>>=1
    return z

def gcd(a,b):
    while b: a,b=b,rem(a,b)
    return a

def irreducible(p,m):
    primes=[]; n=m; d=2
    while d*d<=n:
        if n%d==0:
            primes.append(d)
            while n%d==0: n//=d
        d+=1
    if n>1: primes.append(n)
    checkpoints={m//q for q in primes}
    x=2
    for i in range(1,m+1):
        x=mul(x,x,p)
        if i in checkpoints and gcd(x^2,p)!=1: return False
    return x==2

out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
rows=[]; failures=[]; counts=Counter(); start=time.perf_counter()
def record(row,ok):
    row['passed']=bool(ok); rows.append(row)
    counts[(str(row['m']),row['operation'],'pass' if ok else 'fail')]+=1
    if not ok: failures.append(row)

preflight={}
for m,t in TAPS.items():
    p=(1<<m)|sum(1<<i for i in t)
    assert fields.get_field(m).mod_poly==p
    assert irreducible(p,m)
    a=(1<<(m-1))|0x57
    assert inv(a,p)==power(a,(1<<m)-2,p)
    preflight[m]={'modulus_hex':hex(p),'irreducible':True,'inverse_crosscheck':True}
print('Independent modulus and inverse preflight passed',flush=True)

quotas={'modulo':1500,'add':1500,'subtract':1500,'multiply':2000,'inverse':1500,'divide':1500}
for fi,(m,t) in enumerate(TAPS.items()):
    p=(1<<m)|sum(1<<i for i in t)
    edge=[0,1,2,3,(1<<(m-1)),(1<<m)-1,1<<m,p,p^1,product(p,3),1<<(2*m), (1<<(2*m+1))-1, 1<<4095]
    for op,total in quotas.items():
        n=total//6+(fi<total%6)
        for j in range(n):
            kind='edge' if j<26 else 'random'
            if kind=='edge': a=edge[j%len(edge)]; b=edge[(j*5+1)%len(edge)]
            else:
                width=[m,m,2*m+1,m+17][j%4]
                a=rng.getrandbits(width); b=rng.getrandbits(width)
                if j%13==0: a=1<<rng.randrange(width)
                if j%17==0: b=a
            base=['hex','bin','algebraic'][j%3]
            def encode(v):
                if base=='hex': return '0x'+format(v,'X')
                if base=='bin': return '0b'+format(v,'b')
                return ' + '.join('1' if i==0 else 'x' if i==1 else f'x^{i}' for i in range(v.bit_length()) if (v>>i)&1) or '0'
            payload={'m':m,'operation':op,'a':encode(a),'input_base':base,'trace':j%2==0}
            if op not in ('modulo','inverse'): payload['b']=encode(b)
            ar,br=rem(a,p),rem(b,p)
            undefined=(op=='inverse' and not ar) or (op=='divide' and not br)
            if undefined: expected='domain_error'
            elif op=='modulo': expected=ar
            elif op in ('add','subtract'): expected=ar^br
            elif op=='multiply': expected=mul(ar,br,p)
            elif op=='inverse': expected=inv(ar,p)
            else: expected=mul(ar,inv(br,p),p)
            try:
                response=calculate(CalculateRequest(**payload))
                observed=int(response.result.hex,16)
                ok=observed==expected and int(response.result.bin,2)==expected
                if response.verification: ok=ok and response.verification.passed
            except CalculationError as e:
                observed='domain_error'; ok=undefined
            except Exception as e: observed=f'{type(e).__name__}: {e}'; ok=False
            record({'id':len(rows)+1,'m':m,'operation':op,'kind':kind,'request':payload,'a_hex':hex(a),'b_hex':hex(b),'expected':hex(expected) if isinstance(expected,int) else expected,'observed':hex(observed) if isinstance(observed,int) else observed},ok)
        print(m,op,n,'done',flush=True)

# 500 additional in-process HTTP validation tests; no server or network connection.
with TestClient(app) as client:
    for j in range(500):
        m=list(TAPS)[j%6]; mode=(j//6)%10
        payload={'m':m,'operation':'add','a':'57','b':'83','trace':False}
        expected_status=400; expected_result=None
        if mode==0: payload['a']='-1'
        elif mode==1: payload.update(input_base='bin',a='102')
        elif mode==2: payload.update(input_base='algebraic',a='x^4096')
        elif mode==3: payload.update(operation='inverse',a='0')
        elif mode==4: payload['b']=''
        elif mode==5: payload['m']=164
        elif mode==6: payload['a']=hex(1<<4096)
        elif mode==7: payload['operation']='unknown'; expected_status=422
        elif mode==8:
            payload.update(input_base='algebraic',a='x + x + 1',b='1'); expected_status=200; expected_result=0
        else:
            payload.update(a='{0x57}',b='0x83'); expected_status=200; expected_result=0xd4
        r=client.post('/api/calculate',json=payload); data=r.json()
        ok=r.status_code==expected_status
        if expected_result is not None: ok=ok and int(data.get('result',{}).get('hex','-1'),16)==expected_result
        record({'id':len(rows)+1,'m':m,'operation':'validation','kind':'http','request':payload,'expected_status':expected_status,'observed_status':r.status_code,'response':data if not ok else None},ok)

assert len(rows)==10000
ledger=out/'cases.jsonl'
ledger.write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows),encoding='utf-8')
summary={'seed':SEED,'total':len(rows),'passed':sum(r['passed'] for r in rows),'failed':len(failures),'elapsed_seconds':round(time.perf_counter()-start,3),'python':sys.version,'platform':platform.platform(),'preflight':preflight,'counts':[{'field':m,'operation':op,'passed':counts[(str(m),op,'pass')],'failed':counts[(str(m),op,'fail')]} for m in TAPS for op in [*quotas,'validation']],'kinds':dict(Counter(r['kind'] for r in rows)),'failures':failures,'ledger_sha256':hashlib.sha256(ledger.read_bytes()).hexdigest()}
(out/'results.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2),flush=True)
if failures:
    raise SystemExit(1)
