"""Prepare and hash an exact local HF upload set. Does not create repos or publish."""
import argparse,json,shutil
from pathlib import Path
from build_database import digest

ROOT=Path(__file__).resolve().parent
def prepare(database, output):
 manifest=json.loads(database.with_suffix('.manifest.json').read_text())
 if manifest['sample'] or not all(c['passed'] for c in manifest['checks'].values()):raise ValueError('Incomplete candidate')
 if digest(database)!=manifest['sha256'] or database.stat().st_size!=manifest['bytes']:raise ValueError('Artifact identity changed')
 if manifest['source_rows']!=402786:raise ValueError('Wrong release')
 output.mkdir(parents=True,exist_ok=False)
 for source,target in [(database,'sahie.duckdb'),(database.with_suffix('.manifest.json'),'build-manifest.json'),(database.parent/(database.stem+'-DICTIONARY.md'),'DICTIONARY.md'),(ROOT/'FIELD-GUIDE.md','FIELD-GUIDE.md'),(ROOT/'source-lock.json','source-lock.json')]:
  shutil.copyfile(source,output/target)
 card=(ROOT/'HF-README.md').read_text().replace('**Local publication candidate; not yet hosted or registered.** The Census Bureau\'s',"The Census Bureau's")
 card=card.replace('-- After opening the local sahie.duckdb candidate:',"-- In DuckDB with HTTPFS available:\nATTACH 'https://huggingface.co/datasets/Nason/sahie-database/resolve/main/sahie.duckdb' AS sahie (READ_ONLY);\nUSE sahie;")
 start=card.index('Python and R local examples are in README.md.')
 end=card.index('\n\nThe groups overlap',start)
 card=card[:start]+'''Python and R clients can query this file directly with DuckDB/DBI. The Python
datapond 0.1.5 and CRAN R datapond 0.1.0 clients passed HTTP range tests against
this exact artifact using a temporary registry (DuckDB 1.5.6 and 1.5.5 respectively).
Registry-based access by the `sahie` identifier requires the corresponding registry
entry to be merged. See build-manifest.json for identity and validation, and
[the code repository](https://github.com/ian-nason/sahie-database) for client examples.
'''.rstrip()+card[end:]
 (output/'README.md').write_text(card)
 files=[{'path':p.name,'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(output.iterdir())]
 plan={'status':'prepared_not_uploaded','destination':'Nason/sahie-database','repo_type':'dataset','files':files,
       'requires':'Explicit new-dataset publication authorization and independent Codex and Claude release sign-off'}
 (output/'upload-manifest.json').write_text(json.dumps(plan,indent=2))
 print(json.dumps(plan,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 a=p.parse_args();prepare(a.db,a.output)
