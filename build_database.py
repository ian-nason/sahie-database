"""Build the pinned 2024 SAHIE release without changing existing artifacts."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import time
import urllib.request
import zipfile

import duckdb
from datapond_build import ensure_metadata, build_columns_table, export_dictionary

ROOT = Path(__file__).resolve().parent
SOURCE_PAGE = 'https://www.census.gov/data/datasets/time-series/demo/sahie/estimates-acs.html'
SOURCE_HEADER = 'year version statefips countyfips geocat agecat racecat sexcat iprcat NIPR nipr_moe NUI nui_moe NIC nic_moe PCTUI pctui_moe PCTIC pctic_moe PCTELIG pctelig_moe PCTLIIC pctliic_moe state_name county_name'.split()
COLUMNS = [x.lower() for x in SOURCE_HEADER]
COUNTS = COLUMNS[9:15]
PERCENTS = COLUMNS[15:23]
KEY = ['year','version','statefips','countyfips','agecat','racecat','sexcat','iprcat']
CODES = {
 'geocat': {40:'State geographic identifier',50:'County geographic identifier'},
 'agecat': {0:'Under 65 years',1:'18 to 64 years',2:'40 to 64 years',3:'50 to 64 years',4:'Under 19 years',5:'21 to 64 years',6:'21 to 29 years'},
 'racecat': {0:'All races',1:'White alone, not Hispanic or Latino',2:'Black or African American alone, not Hispanic',3:'Hispanic or Latino (any race)',4:'American Indian and Alaska Native alone, not Hispanic or Latino',5:'Asian alone, not Hispanic or Latino',6:'Native Hawaiian and Other Pacific Islander alone, not Hispanic or Latino',7:'Two or More Races, not Hispanic or Latino'},
 'sexcat': {0:'Both sexes',1:'Male',2:'Female'},
 'iprcat': {0:'All income levels',1:'At or below 200% of poverty',2:'At or below 250% of poverty',3:'At or below 138% of poverty',4:'At or below 400% of poverty',5:'Between 138% - 400% of poverty'},
}
DESCRIPTIONS = {
 'estimates':'2024 model-based state/county health-insurance estimates, overlapping demographic/income groups; published 90% margins of error retained',
 'geographies':'State and county identifiers/names observed in this release; FIPS strings retain leading zeros',
 'category_codes':'Definitions of the five categorical fields from the official SAHIE file preamble',
}

def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  while b:=f.read(1024*1024): h.update(b)
 return h.hexdigest()

def acquire(lock, target):
 target=Path(target)
 if target.exists():
  if target.stat().st_size!=lock['bytes'] or digest(target)!=lock['sha256']:
   raise ValueError('Cached source does not match the lock; preserved unchanged')
  return target
 target.parent.mkdir(parents=True,exist_ok=True)
 partial=target.with_suffix(target.suffix+'.part')
 if partial.exists(): raise FileExistsError(f'Preserve prior incomplete download: {partial}')
 n=0
 with urllib.request.urlopen(lock['url'],timeout=30) as response, partial.open('xb') as out:
  while block:=response.read(65536):
   n+=len(block)
   if n>lock['bytes'] or n>20*1024**2: raise ValueError('Download exceeded pinned size or 20 MiB limit')
   out.write(block)
 if n!=lock['bytes'] or digest(partial)!=lock['sha256']:
  raise ValueError('Source changed since pinned release; incomplete source retained for review')
 partial.rename(target)
 return target

def validate_preamble(lines):
 found={name:{} for name in CODES}; category=None
 for line in lines:
  line=' '.join(line.split())
  first=line.split(' ',1)[0]
  if first in CODES: category=first
  match=re.fullmatch(r'([0-9]+) - (.+)',line)
  if category and match:
   found[category][int(match[1])]=match[2]
 if found!=CODES: raise ValueError('Source preamble category definitions changed')

def source_rows(stream, check_preamble=False):
 """Strictly read the documented preamble/header and blank trailing CSV field."""
 reader=csv.reader(stream);preamble=[]
 for _ in range(150):
  row=next(reader,None)
  if row is None: raise ValueError('SAHIE header missing')
  if row and row[0]=='year':
   if row != SOURCE_HEADER+['']: raise ValueError('Unexpected SAHIE schema')
   if check_preamble: validate_preamble(preamble)
   break
  preamble.append(','.join(row))
 else: raise ValueError('SAHIE header not found within bounded preamble')
 for number,row in enumerate(reader,1):
  if len(row)!=len(SOURCE_HEADER)+1 or row[-1].strip():
   raise ValueError(f'Malformed source row {number}')
  row=[v.strip() for v in row[:-1]]
  if row[0]!='2024' or row[1] or not re.fullmatch(r'[0-9]{2}',row[2]) or not re.fullmatch(r'[0-9]{3}',row[3]):
   raise ValueError(f'Unexpected year/version/FIPS at row {number}')
  for name in CODES:
   if row[COLUMNS.index(name)] not in {str(x) for x in CODES[name]}:
    raise ValueError(f'Unknown {name} at row {number}')
  for idx in range(9,23):
   value=row[idx]
   if value=='.': continue
   valid=re.fullmatch(r'[0-9]+',value) if idx<15 else re.fullmatch(r'[0-9]+(?:\.[0-9])?',value)
   if not value or not valid:
    raise ValueError(f'Unexpected numeric token {value!r} at row {number}')
  yield row+[str(number)]

def normalize(archive,destination,limit=None,lock=None):
 with zipfile.ZipFile(archive) as z:
  if z.namelist()!=['sahie_2024.csv']: raise ValueError('Unexpected archive members')
  if z.getinfo('sahie_2024.csv').file_size>120*1024**2: raise ValueError('Archive expansion exceeds 120MiB')
  if lock and 'members' in lock:
   actual=z.getinfo('sahie_2024.csv')
   if lock['members']!=[{'name':actual.filename,'bytes':actual.file_size,'crc32':actual.CRC}]: raise ValueError('Archive member identity differs')
  count=0
  with z.open('sahie_2024.csv') as raw, io.TextIOWrapper(raw,encoding='utf-8-sig',newline='') as text, Path(destination).open('x',newline='',encoding='utf-8') as out:
   writer=csv.writer(out)
   writer.writerow(COLUMNS+['source_row'])
   for row in source_rows(text,check_preamble=True):
    writer.writerow(row);count+=1
    if limit and count>=limit: break
 return count

def validate(con,expected,complete):
 checks={}
 def check(name,sql,want):
  value=con.execute(sql).fetchone()[0]
  checks[name]={'actual':value,'expected':want,'passed':value==want}
  if value!=want: raise ValueError(f'{name}: {value!r} != {want!r}')
 check('source_row_count','SELECT count(*) FROM estimates',expected)
 check('unique_keys',f'SELECT count(*) FROM (SELECT {",".join(KEY)} FROM estimates GROUP BY ALL HAVING count(*)>1)',0)
 check('nonmissing_keys','SELECT count(*) FROM estimates WHERE '+ ' OR '.join(f'{c} IS NULL' for c in KEY),0)
 check('geography_consistency',"SELECT count(*) FROM estimates WHERE (geocat=40 AND countyfips<>'000') OR (geocat=50 AND countyfips='000') OR (geocat=50 AND racecat<>0)",0)
 check('under19_categories','SELECT count(*) FROM estimates WHERE agecat=4 AND (racecat<>0 OR sexcat<>0)',0)
 check('count_identity','SELECT count(*) FROM estimates WHERE nipr IS NOT NULL AND nipr<>nui+nic',0)
 check('measure_moe_missingness','SELECT count(*) FROM estimates WHERE '+' OR '.join(f'({c} IS NULL)<>({c}_moe IS NULL)' for c in ['nipr','nui','nic','pctui','pctic','pctelig','pctliic']),0)
 check('count_missingness','SELECT count(*) FROM estimates WHERE (nipr IS NULL)<>(nui IS NULL) OR (nipr IS NULL)<>(nic IS NULL)',0)
 check('percent_pair_missingness','SELECT count(*) FROM estimates WHERE (pctui IS NULL)<>(pctic IS NULL) OR (pctelig IS NULL)<>(pctliic IS NULL)',0)
 check('percentage_complement','SELECT count(*) FROM estimates WHERE pctui IS NOT NULL AND abs(pctui+pctic-100)>0.1',0)
 check('percentage_range','SELECT count(*) FROM estimates WHERE '+' OR '.join(f'{c}<0 OR {c}>100' for c in PERCENTS),0)
 check('nonnegative_counts','SELECT count(*) FROM estimates WHERE '+' OR '.join(f'{c}<0' for c in COUNTS),0)
 check('geography_unique','SELECT count(*) FROM (SELECT fips FROM geographies GROUP BY fips HAVING count(*)>1)',0)
 check('all_income_percentages', '''SELECT count(*) FROM estimates WHERE iprcat=0 AND
 (pctelig IS DISTINCT FROM pctui OR (pctliic IS NULL)<>(pctic IS NULL) OR abs(pctliic-pctic)>0.1)''',0)
 check('eligible_vs_within_income','SELECT count(*) FROM estimates WHERE pctelig>pctui',0)
 check('all_income_denominator', '''SELECT count(*) FROM estimates e JOIN estimates base
 USING(year,version,statefips,countyfips,geocat,agecat,racecat,sexcat)
 WHERE base.iprcat=0 AND base.nipr>0 AND abs(e.pctelig+e.pctliic-100.0*e.nipr/base.nipr)>0.101''',0)
 if complete:
  check('complete_2024_rows','SELECT count(*) FROM estimates',402786)
  check('states','SELECT count(*) FROM geographies WHERE geocat=40',51)
  check('counties','SELECT count(*) FROM geographies WHERE geocat=50',3144)
  check('county_view_grain','SELECT count(*) FROM county_uninsured',3144)
  check('kalawao_missing',"SELECT count(*) FROM estimates WHERE statefips='15' AND countyfips='005' AND ("+' OR '.join(f'{c} IS NOT NULL' for c in COUNTS+PERCENTS)+')',0)
 return checks

def build(archive,output,lock,limit=None):
 start=time.monotonic(); output=Path(output)
 output.parent.mkdir(parents=True,exist_ok=True)
 partial=output.with_suffix('.partial.duckdb'); normalized=output.with_suffix('.normalized.csv')
 for p in [output,Path(str(output)+'.wal'),partial,Path(str(partial)+'.wal'),normalized,output.with_suffix('.manifest.json'),output.parent/(output.stem+'-DICTIONARY.md')]:
  if p.exists(): raise FileExistsError(f'Refusing to overwrite {p}')
 if shutil.disk_usage(output.parent).free<512*1024**2: raise RuntimeError('Less than 512MiB free')
 if archive.stat().st_size!=lock['bytes'] or digest(archive)!=lock['sha256']: raise ValueError('Unpinned source')
 rows=normalize(archive,normalized,limit,lock)
 types={c:('VARCHAR' if c in ['version','statefips','countyfips','state_name','county_name'] else 'DECIMAL(5,1)' if c in PERCENTS else 'BIGINT' if c in COUNTS else 'INTEGER') for c in COLUMNS}
 types['source_row']='BIGINT'
 config={'memory_limit':'256MiB','threads':'1','max_temp_directory_size':'0B','preserve_insertion_order':'true'}
 con=duckdb.connect(str(partial),config=config)
 try:
  schema='{'+','.join(f"'{c}':'{t}'" for c,t in types.items())+'}'
  con.execute(f"CREATE TABLE estimates AS SELECT * FROM read_csv(?,header=true,columns={schema},nullstr='.',strict_mode=true)",[str(normalized)])
  con.execute("ALTER TABLE estimates ADD COLUMN fips VARCHAR")
  con.execute("UPDATE estimates SET fips=CASE WHEN geocat=40 THEN statefips ELSE statefips||countyfips END")
  con.execute("CREATE TABLE geographies AS SELECT DISTINCT fips,statefips,countyfips,geocat,state_name,NULLIF(county_name,'') AS county_name FROM estimates")
  con.execute('CREATE TABLE category_codes(category VARCHAR,code INTEGER,label VARCHAR,PRIMARY KEY(category,code))')
  con.executemany('INSERT INTO category_codes VALUES (?,?,?)',[(name,code,label) for name,codes in CODES.items() for code,label in codes.items()])
  con.execute('CREATE VIEW county_uninsured AS SELECT year,fips,statefips,countyfips,state_name,county_name,nipr,nipr_moe,nui,nui_moe,nic,nic_moe,pctui,pctui_moe,pctic,pctic_moe FROM estimates WHERE geocat=50 AND agecat=0 AND racecat=0 AND sexcat=0 AND iprcat=0')
  con.execute('CREATE TABLE _provenance(source_url VARCHAR,source_sha256 VARCHAR,source_bytes BIGINT,source_member VARCHAR,source_retrieved_utc VARCHAR,release_label VARCHAR,source_rows BIGINT,is_sample BOOLEAN)')
  con.execute('INSERT INTO _provenance VALUES (?,?,?,?,?,?,?,?)',[lock['url'],lock['sha256'],lock['bytes'],'sahie_2024.csv',lock['retrieved_utc'],'2024 estimates; August 2026 release',rows,limit is not None])
  tables=list(DESCRIPTIONS)
  ensure_metadata(con,tables=tables,descriptions=DESCRIPTIONS,source_url=SOURCE_PAGE,license='U.S. public domain (Census Bureau work)')
  build_columns_table(con,tables=tables,join_hints={'fips':'Use geography level and year; county FIPS is five characters. Match geographic vintages before joining.','statefips':'Two-character state FIPS, preserving leading zeros.','countyfips':'Three-character code within state; combine with statefips.','agecat':'category_codes where category=agecat; groups overlap.','racecat':'category_codes where category=racecat; detailed race is state-only.','sexcat':'category_codes where category=sexcat','iprcat':'category_codes where category=iprcat; nested income groups overlap.'})
  checks=validate(con,rows,limit is None)
  check_columns=con.execute('SELECT count(*) FROM _columns WHERE null_pct IS NULL').fetchone()[0]
  if check_columns: raise ValueError('Column dictionary statistics incomplete')
  export_dictionary(con,output.parent/(output.stem+'-DICTIONARY.md'),title='SAHIE 2024 data dictionary',tables=tables,intro=['Source: U.S. Census Bureau, August 2026 release. All MOEs are at 90% confidence.','See FIELD-GUIDE.md for measure definitions, overlap warnings and missing-value policy.'])
  counts=dict(con.execute('SELECT table_name,row_count FROM _metadata').fetchall())
  nulls=dict(zip(COUNTS+PERCENTS,con.execute('SELECT '+','.join(f'count(*) FILTER (WHERE {c} IS NULL)' for c in COUNTS+PERCENTS)+' FROM estimates').fetchone()))
  dictionary=output.parent/(output.stem+'-DICTIONARY.md')
  content=dictionary.read_text()
  for column,count in nulls.items():
   if count:
    content=re.sub(r'(\| '+re.escape(column)+r' \| [^|]+ \| )0\.0%( \|)',rf'\g<1>{count:,} (<0.1%)\2',content)
  dictionary.write_text(content)
  con.execute('CHECKPOINT')
 finally: con.close()
 partial.rename(output)
 # Only this freshly generated, verified intermediate belongs to this build.
 normalized.unlink()
 record={'built_utc':datetime.now(timezone.utc).isoformat(),'source':lock,'source_rows':rows,'sample':limit is not None,'tables':counts,'null_counts':nulls,'checks':checks,'output':output.name,'bytes':output.stat().st_size,'sha256':digest(output),'duckdb':duckdb.__version__,'config':config,'elapsed_seconds':round(time.monotonic()-start,3)}
 with output.with_suffix('.manifest.json').open('x') as stream: json.dump(record,stream,indent=2)
 print(json.dumps({k:v for k,v in record.items() if k not in ('source','checks','null_counts')},indent=2))
 return record

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--source',type=Path,default=ROOT/'data/sahie-2024-csv.zip')
 parser.add_argument('--output',type=Path,default=ROOT/'data/sahie.duckdb')
 parser.add_argument('--sample-rows',type=int)
 args=parser.parse_args()
 if args.sample_rows is not None and args.sample_rows<=0: parser.error('sample rows must be positive')
 lock=json.loads((ROOT/'source-lock.json').read_text())
 build(acquire(lock,args.source),args.output,lock,args.sample_rows)

if __name__=='__main__': main()
