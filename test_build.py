import csv, io, tempfile, unittest, zipfile
from pathlib import Path
import duckdb
import build_database as b

ROW=['2024','','01','001','50','0','0','0','0','100','0','10','2','90','2','10.0','2.0','90.0','2.0','10.0','2.0','90.0','2.0','Alabama','Autauga County','']
def source(rows,header=None):
 f=io.StringIO();w=csv.writer(f);w.writerow(['Official preamble'])
 for category,codes in b.CODES.items():
  w.writerow([category+' 1 Category'])
  for code,label in codes.items():w.writerow([str(code)+' - '+label])
 w.writerow(header or b.SOURCE_HEADER+['']);w.writerows(rows);f.seek(0);return f

class IngestionTests(unittest.TestCase):
 def test_leading_zeroes_and_blank_version(self):
  r=list(b.source_rows(source([ROW])))[0]
  self.assertEqual(r[1:4],['','01','001']);self.assertEqual(r[-1],'1')
 def test_source_missing_marker(self):
  row=ROW.copy();row[2:4]=['15','005'];row[9:23]=['.']*14
  self.assertEqual(list(b.source_rows(source([row])))[0][9:23],['.']*14)
 def test_schema_drift(self):
  with self.assertRaisesRegex(ValueError,'schema'):list(b.source_rows(source([ROW],b.SOURCE_HEADER+['unexpected'])))
 def test_extra_trailing_data(self):
  row=ROW.copy();row[-1]='lost-data'
  with self.assertRaisesRegex(ValueError,'Malformed'):list(b.source_rows(source([row])))
 def test_fractional_count_and_unknown_sentinel(self):
  for value in ['3.5','-999','NA','','١٠']:
   row=ROW.copy();row[9]=value
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'numeric'):list(b.source_rows(source([row])))
 def test_unknown_category_and_year(self):
  for col,value in [(5,'9'),(0,'2025')]:
   row=ROW.copy();row[col]=value
   with self.assertRaises(ValueError):list(b.source_rows(source([row])))
 def test_new_age_and_preamble_drift(self):
  row=ROW.copy();row[5]='6'
  self.assertEqual(list(b.source_rows(source([row]),check_preamble=True))[0][5],'6')
  with self.assertRaisesRegex(ValueError,'definitions'):
   list(b.source_rows(io.StringIO(source([ROW]).getvalue().replace('21 to 29 years','21 to 30 years')),check_preamble=True))
 def test_excess_precision_rejected(self):
  row=ROW.copy();row[15]='10.01'
  with self.assertRaisesRegex(ValueError,'numeric'):list(b.source_rows(source([row])))
 def test_unpinned_cache_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source.zip';p.write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'Cached'):b.acquire({'bytes':7,'sha256':'0'*64},p)
   self.assertEqual(p.read_bytes(),b'changed')
 def test_unexpected_zip_member(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'source.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('../escape.csv','x')
   with self.assertRaisesRegex(ValueError,'members'):b.normalize(p,Path(d)/'out.csv')
 def test_existing_sidecars_preserved(self):
  for filename in ['candidate.manifest.json','candidate-DICTIONARY.md']:
   with self.subTest(filename=filename), tempfile.TemporaryDirectory() as d:
    d=Path(d);sidecar=d/filename;sidecar.write_text('prior work')
    with self.assertRaises(FileExistsError):b.build(d/'not-downloaded.zip',d/'candidate.duckdb',{})
    self.assertEqual(sidecar.read_text(),'prior work')
 def test_integration_missing_duplicate_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);p=d/'fixture.zip'
   row=ROW.copy();row[2:4]=['15','005'];row[9:23]=['.']*14;row[23:25]=['Hawaii','Kalawao County']
   with zipfile.ZipFile(p,'w') as z:z.writestr('sahie_2024.csv',source([ROW,row]).getvalue())
   lock={'bytes':p.stat().st_size,'sha256':b.digest(p),'url':'https://example.invalid/fixture','retrieved_utc':'fixture'}
   b.build(p,d/'fixture.duckdb',lock,limit=2)
   with duckdb.connect(str(d/'fixture.duckdb'),read_only=True) as c:
    self.assertEqual(c.execute('SELECT fips,pctui FROM county_uninsured ORDER BY fips').fetchall(),[('01001',10),('15005',None)])
    self.assertEqual(c.execute('SELECT count(*) FROM _metadata').fetchone()[0],3)
   self.assertIn('| nipr | BIGINT | 50.0% |', (d/'fixture-DICTIONARY.md').read_text())
   with self.assertRaises(FileExistsError):b.build(p,d/'fixture.duckdb',lock,limit=2)
   with zipfile.ZipFile(p,'w') as z:z.writestr('sahie_2024.csv',source([ROW,ROW]).getvalue())
   lock.update(bytes=p.stat().st_size,sha256=b.digest(p))
   with self.assertRaisesRegex(ValueError,'unique_keys'):b.build(p,d/'duplicate.duckdb',lock,limit=2)
   self.assertFalse((d/'duplicate.duckdb').exists())
 def test_validation_rejects_invalid_categories_and_denominators(self):
  mutations=[(6,'1','geography_consistency'),(5,'4','under19_categories'),(19,'9.0','all_income_percentages'),(10,'.','measure_moe_missingness')]
  for column,value,error in mutations:
   with self.subTest(error=error),tempfile.TemporaryDirectory() as directory:
    d=Path(directory);row=ROW.copy();row[column]=value
    if error=='under19_categories':row[7]='1'
    p=d/'fixture.zip'
    with zipfile.ZipFile(p,'w') as z:z.writestr('sahie_2024.csv',source([row]).getvalue())
    lock={'bytes':p.stat().st_size,'sha256':b.digest(p),'url':'https://example.invalid','retrieved_utc':'fixture'}
    with self.assertRaisesRegex(ValueError,error):b.build(p,d/'invalid.duckdb',lock,limit=1)
    self.assertFalse((d/'invalid.duckdb').exists())
 def test_published_one_decimal_rounding_is_preserved(self):
  with tempfile.TemporaryDirectory() as directory:
   d=Path(directory);row=ROW.copy();row[9]='2000';row[11]='347';row[13]='1653'
   row[15]='17.4';row[17]='82.6';row[19]='17.4';row[21]='82.7'
   p=d/'fixture.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('sahie_2024.csv',source([row]).getvalue())
   lock={'bytes':p.stat().st_size,'sha256':b.digest(p),'url':'https://example.invalid','retrieved_utc':'fixture'}
   b.build(p,d/'rounded.duckdb',lock,limit=1)
   with duckdb.connect(str(d/'rounded.duckdb'),read_only=True) as con:
    self.assertEqual(str(con.execute('SELECT pctliic-pctic FROM estimates').fetchone()[0]),'0.1')

if __name__=='__main__':unittest.main(verbosity=2)
