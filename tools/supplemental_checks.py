"""Focused regressions separate from the 10,000-case campaign."""
import sys,json,time,statistics
from pathlib import Path
import argparse
cli=argparse.ArgumentParser()
cli.add_argument('--repo',default='.')
cli.add_argument('--deps',default='.')
cli.add_argument('--out',default='audit-results')
args=cli.parse_args()
root=Path(args.out).resolve(); root.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(Path(args.deps).resolve()),str(Path(args.repo).resolve())]
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.engine.explorations import gcm_ghash
from backend.engine.extended_euclid import EXTENDED_EUCLID_GF2M
from backend.api.services import calculate
from backend.api.schemas import CalculateRequest

def nist_mul(x,y):
    z=0; v=y
    for i in range(128):
        if (x>>(127-i))&1: z^=v
        v=(v>>1)^((0xe1<<120) if v&1 else 0)
    return z

results=[]
for h,blocks in [('80000000000000000000000000000000',['00000000000000000000000000000001']),('66e94bd4ef8a2c3b884cfa59ca342b2e',['0388dace60b6a392f328c2b971b2fe78']),('66e94bd4ef8a2c3b884cfa59ca342b2e',['0388dace60b6a392f328c2b971b2fe78','00000000000000000000000000000080'])]:
    y=0
    for b in blocks: y=nist_mul(y^int(b,16),int(h,16))
    actual=gcm_ghash(h,blocks)['tag_hex']
    results.append({'check':'NIST GHASH','h':h,'blocks':blocks,'expected':f'{y:032X}','actual':actual,'passed':int(actual,16)==y})
with TestClient(app) as c:
    parsecases=[('grouped_hex',{'content':'A: 0xAB CD\nB: 01','filename':'test.txt'},200),('bom_json',{'content':'\ufeff[{"a":"57","b":"83"}]','filename':'test.json'},200),('duplicate_label',{'content':'A: 57\nA: 83','filename':'test.txt'},400),('bad_json',{'content':'[{','filename':'test.json'},400),('algebraic_batch',{'content':'A: x + 1\nB: 1','filename':'test.txt','default_base':'algebraic'},200)]
    for name,payload,status in parsecases:
        r=c.post('/api/parse-polynomials',json=payload)
        results.append({'check':name,'request':payload,'expected_status':status,'actual_status':r.status_code,'response':r.json(),'passed':r.status_code==status})
    large='1'+'0'*1024
    parsed=c.post('/api/parse-polynomials',json={'filename':'big.json','content':json.dumps({'a':large,'b':'1'})})
    calculated=c.post('/api/calculate',json={'m':163,'operation':'add','a':large,'b':'1','trace':False})
    results.append({'check':'upload/calculator width consistency','a_recipe':"'1' + '0'*1024 (hex)",'parse_status':parsed.status_code,'calculate_status':calculated.status_code,'calculate_response':calculated.json(),'passed':parsed.status_code==calculated.status_code})
    coercions={}
    for m in ['163',163.0]:
        r=c.post('/api/calculate',json={'m':m,'operation':'add','a':'1','b':'1','trace':False})
        coercions[repr(m)]=r.status_code

# Evidence that trace=false still invokes row construction in inverse.
import backend.engine.extended_euclid as eea
original=eea._build_table_4_7_row
calls=[0]
def counted(*a,**kw): calls[0]+=1; return original(*a,**kw)
eea._build_table_4_7_row=counted
calculate(CalculateRequest(m=571,operation='inverse',a='123456789ABCDEF',trace=False))
eea._build_table_4_7_row=original
report={'checks':results,'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),'inverse_trace_false_rows_built':calls[0],'field_type_coercion_http_status':coercions,'nist_source':'https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-38d.pdf'}
(root/'supplemental-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if report['failed'] or report['inverse_trace_false_rows_built']:
    raise SystemExit(1)
