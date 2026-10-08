#!/bin/bash
set -euo pipefail
# Initialization runs only on a new volume. Passwords must be generated safe strings.
for value in "$MYSQL_USER" "$MYSQL_DATABASE" "$ERP_ADMIN_PASSWORD" "$ERP_TENANT_PASSWORD"; do
  [[ "$value" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Unsupported characters in initialization value'; exit 1; }
done
admin_hash=$(printf '%s' "$ERP_ADMIN_PASSWORD" | md5sum | cut -d' ' -f1)
tenant_hash=$(printf '%s' "$ERP_TENANT_PASSWORD" | md5sum | cut -d' ' -f1)
MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot "$MYSQL_DATABASE" <<SQL
UPDATE jsh_user SET password='$admin_hash' WHERE login_name='admin';
UPDATE jsh_user SET password='$tenant_hash' WHERE login_name='jsh';
UPDATE jsh_user SET status=1 WHERE login_name='test123';
REVOKE ALL PRIVILEGES, GRANT OPTION FROM '$MYSQL_USER'@'%';
GRANT SELECT,INSERT,UPDATE,DELETE ON \`$MYSQL_DATABASE\`.* TO '$MYSQL_USER'@'%';
SQL
