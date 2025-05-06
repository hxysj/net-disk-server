import pymysql
from datetime import datetime

db_config = {
    'host': '127.0.0.1',
    'user': 'root', 
    'password': '2003010230',  
    'database': 'netdisk', 
    'charset': 'utf8mb4', 
}

batch_size = 1000
connection = pymysql.connect(**db_config)
now_time = datetime.now()

try:
    with connection.cursor() as cursor:
        while True:

            query = """
            SELECT share_id FROM file_share WHERE expire_time < %s LIMIT %s
            """
            cursor.execute(query, (now_time, batch_size))
            expired_records = cursor.fetchall()

            if expired_records:
                print(f"发现 {len(expired_records)} 条过期记录，正在删除...")
                expired_ids = [record[0] for record in expired_records]
                print(expired_ids)
                delete_query = "DELETE FROM file_share WHERE share_id IN (%s)"
                format_strings = ','.join(['%s'] * len(expired_ids))
                delete_query = delete_query % format_strings
                cursor.execute(delete_query, expired_ids)
                connection.commit()
                print(f"成功删除了 {len(expired_ids)} 条记录。")
            else:
                print("没有更多的过期记录。")
                break

finally:
    connection.close()
