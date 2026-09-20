source ~/.bashrc && cd ~/frappe-bench && bench --site kayanos.localhost mariadb -e "SELECT name FROM tabWorkspace WHERE is_hidden=0;"
