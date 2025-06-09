from discord_agents.core.database import engine
from sqlalchemy import text


def check_database_schema():
    with engine.connect() as conn:
        # 檢查所有表
        result = conn.execute(
            text(
                """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
            )
        )
        tables = [row[0] for row in result.fetchall()]
        print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")

        # 檢查核心表結構
        for table in ["my_bots", "my_agents", "notes"]:
            if table in tables:
                print(f"\n🔍 Table: {table}")
                result = conn.execute(
                    text(
                        f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = '{table}'
                    ORDER BY ordinal_position
                """
                    )
                )
                for row in result:
                    nullable = "NULL" if row[2] == "YES" else "NOT NULL"
                    default = f" DEFAULT {row[3]}" if row[3] else ""
                    print(f"  - {row[0]}: {row[1]} {nullable}{default}")

        # 檢查外鍵約束
        print(f"\n🔗 Foreign Key Constraints:")
        result = conn.execute(
            text(
                """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name IN ('my_bots', 'my_agents', 'notes')
        """
            )
        )
        for row in result:
            print(f"  {row[0]}.{row[1]} -> {row[2]}.{row[3]}")


if __name__ == "__main__":
    check_database_schema()
