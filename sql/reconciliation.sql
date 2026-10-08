-- Read only. Run on this project's isolated jsh_erp schema. Filter tenant 63.
SELECT VERSION(), @@character_set_server, @@collation_server;
SELECT type, COUNT(*) AS migrated_records FROM jsh_supplier
WHERE tenant_id=63 AND description LIKE 'legacy-code:%' AND delete_flag='0' GROUP BY type;
SELECT me.bar_code,m.name,m.unit,d.name AS warehouse,
       COALESCE(i.number,0) AS initial_quantity,c.current_number
FROM jsh_material m JOIN jsh_material_extend me ON me.material_id=m.id
JOIN jsh_material_current_stock c ON c.material_id=m.id
JOIN jsh_depot d ON d.id=c.depot_id
LEFT JOIN jsh_material_initial_stock i ON i.material_id=m.id AND i.depot_id=d.id
WHERE me.tenant_id=63 AND me.bar_code LIKE 'FP-MAT-%' AND me.delete_flag='0'
ORDER BY me.bar_code,d.id;
-- Native forced-approval=1: only approved stock documents count. Other/order types do not.
SELECT me.bar_code,d.name,
       COALESCE(i.number,0) AS initial_quantity,
       COALESCE(SUM(CASE WHEN dh.status='1' AND dh.type='入库' THEN di.basic_number
                        WHEN dh.status='1' AND dh.type='出库' THEN -di.basic_number ELSE 0 END),0) AS net_movement,
       c.current_number,
       c.current_number-COALESCE(i.number,0)-COALESCE(SUM(CASE
         WHEN dh.status='1' AND dh.type='入库' THEN di.basic_number
         WHEN dh.status='1' AND dh.type='出库' THEN -di.basic_number ELSE 0 END),0) AS difference
FROM jsh_material_extend me JOIN jsh_material_current_stock c ON c.material_id=me.material_id
JOIN jsh_depot d ON d.id=c.depot_id
LEFT JOIN jsh_material_initial_stock i ON i.material_id=me.material_id AND i.depot_id=c.depot_id AND i.delete_flag='0'
LEFT JOIN jsh_depot_item di ON di.material_id=me.material_id AND di.depot_id=c.depot_id AND di.delete_flag='0'
LEFT JOIN jsh_depot_head dh ON dh.id=di.header_id AND dh.delete_flag='0'
WHERE me.tenant_id=63 AND me.bar_code LIKE 'FP-MAT-%' AND me.delete_flag='0' AND c.delete_flag='0'
GROUP BY me.bar_code,d.name,i.number,c.current_number ORDER BY me.bar_code,d.name;
SELECT dh.number,dh.type,dh.sub_type,dh.status,dh.purchase_status,dh.creator,dh.link_number,
       me.bar_code,di.oper_number,di.basic_number,di.depot_id,di.link_id
FROM jsh_depot_head dh JOIN jsh_depot_item di ON di.header_id=dh.id
JOIN jsh_material_extend me ON me.id=di.material_extend_id
WHERE dh.tenant_id=63 AND dh.number LIKE 'FP-%' AND dh.delete_flag='0' AND di.delete_flag='0'
ORDER BY dh.id;
SELECT tenant_id,bar_code,COUNT(*) AS copies FROM jsh_material_extend
WHERE tenant_id=63 AND bar_code LIKE 'FP-MAT-%' AND delete_flag='0'
GROUP BY tenant_id,bar_code HAVING COUNT(*)>1;
SELECT description,COUNT(*) AS copies FROM jsh_supplier
WHERE tenant_id=63 AND description LIKE 'legacy-code:%' AND delete_flag='0'
GROUP BY description HAVING COUNT(*)>1;
SELECT number,COUNT(*) AS copies FROM jsh_depot_head
WHERE tenant_id=63 AND number LIKE 'FP-%' AND delete_flag='0'
GROUP BY number HAVING COUNT(*)>1;
