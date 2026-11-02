"""Exercise the released client against an isolated loopback registry/artifact."""
import json,sys,importlib.metadata
from decimal import Decimal
from pathlib import Path
import datapond,datapond.registry as registry,duckdb
registry.REGISTRY_URL=sys.argv[1]
registry.CACHE_DIR=Path(sys.argv[2]);registry.CACHE_FILE=registry.CACHE_DIR/'registry.json'
probe=duckdb.connect()
assert probe.execute("SELECT installed FROM duckdb_extensions() WHERE extension_name='httpfs'").fetchone()[0], 'Use an already installed httpfs extension'
probe.close()
assert datapond.list()==['sahie']
con=datapond.connect('sahie',quiet=True)
try:
 con.execute("SET memory_limit='128MiB'");con.execute('SET threads=1');con.execute("SET max_temp_directory_size='0B'")
 assert con.execute('SELECT count(*) FROM estimates').fetchone()[0]==402786
 assert con.execute('SELECT count(*) FROM county_uninsured').fetchone()[0]==3144
 assert con.execute('SELECT count(*) FROM _metadata').fetchone()[0]==3
 assert con.execute('SELECT count(*) FROM _columns').fetchone()[0]==36
 assert con.execute("SELECT count(*) FROM county_uninsured WHERE fips='15005' AND pctui IS NULL").fetchone()[0]==1
 assert con.execute("SELECT fips FROM county_uninsured WHERE fips='01001'").fetchone()[0]=='01001'
 assert isinstance(con.execute("SELECT pctui FROM county_uninsured WHERE fips='01001'").fetchone()[0],Decimal)
 example=con.execute("SELECT fips,county_name,pctui,pctui_moe FROM county_uninsured WHERE statefips='36' ORDER BY fips LIMIT 3").fetchall()
 print(json.dumps({'passed':True,'client':'Python datapond','version':importlib.metadata.version('datapond'),'duckdb':duckdb.__version__,'example':example},default=str))
finally:con.close()
