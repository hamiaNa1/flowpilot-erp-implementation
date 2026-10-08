from common import query, write_json
result={
 'functions':query("SELECT id,name,url,number,parent_number,push_btn FROM jsh_function WHERE delete_flag='0'"),
 'config':query("SELECT * FROM jsh_system_config WHERE tenant_id=63 AND delete_flag='0'"),
 'stocks':query("SELECT me.bar_code,m.name,d.name depot,c.current_number FROM jsh_material_extend me JOIN jsh_material m ON me.material_id=m.id JOIN jsh_material_current_stock c ON c.material_id=m.id JOIN jsh_depot d ON d.id=c.depot_id WHERE me.bar_code LIKE 'FP-MAT-%'"),
 'db':query('SELECT VERSION() version,@@character_set_server charset,@@collation_server collation'),
}
write_json('evidence/native-contract.json',result)
print([(f['id'],f['name'],f['url']) for f in result['functions'] if any(x in f['name'] for x in ['采购','销售','库存','商品','供应','客户','入库','出库'])])
