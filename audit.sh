echo '=== ALL CUSTOM FIELDS ON PROJECT ==='
bench --site kayanos.localhost mariadb -e "SELECT fieldname FROM \"tabCustom Field\" WHERE dt='Project';"
