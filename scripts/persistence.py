from common import query, write_json, now, ENV
from native import start, stop, port_open

def snapshot():
    return {
      'stocks':query("SELECT me.bar_code,d.name,c.current_number FROM jsh_material_current_stock c JOIN jsh_material_extend me ON me.material_id=c.material_id JOIN jsh_depot d ON d.id=c.depot_id WHERE me.bar_code LIKE 'FP-MAT-%' ORDER BY me.bar_code,d.id"),
      'bills':query("SELECT id,number,status,link_number,total_price FROM jsh_depot_head WHERE number LIKE 'FP-%' AND delete_flag='0' ORDER BY id"),
      'masters':query("SELECT id,supplier,type,description FROM jsh_supplier WHERE tenant_id=63 AND description LIKE 'legacy-code:%' ORDER BY id")}

before=snapshot(); stop()
stopped={k:not port_open(ENV[k]) for k in ['MYSQL_PORT','REDIS_PORT','BACKEND_PORT','HTTP_PORT']}
start(); after=snapshot()
write_json('evidence/persistence-restart.json',{'time':now(),'before':before,'all_ports_stopped':stopped,'after':after,'data_equal':before==after,'deployment':'Windows portable processes; container restart NOT EXECUTED'})
assert before==after and all(stopped.values())
print('All four services stopped and restarted; business/master/stock data unchanged.')
