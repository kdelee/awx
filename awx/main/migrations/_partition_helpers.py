from django.db import connection


def inbound_constraints(table_names):
    """Return inbound FK metadata before an execution-table swap."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE confrelid = ANY(%s::regclass[])
            ORDER BY conrelid::regclass::text, conname
            """,
            [list(table_names)],
        )
        return cursor.fetchall()


def index_definitions(table_names):
    """Capture index definitions, excluding indexes owned by constraints."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = ANY(%s)
              AND indexname NOT IN (
                SELECT indexrelid::regclass::text
                FROM pg_index
                WHERE indisprimary OR indisunique
                  AND EXISTS (
                    SELECT 1 FROM pg_constraint c
                    WHERE c.conindid = pg_index.indexrelid
                  )
              )
            ORDER BY tablename, indexname
            """,
            [list(table_names)],
        )
        return cursor.fetchall()


def rewrite_partition_constraint(definition, table_names):
    """Point a captured FK definition at the new partitioned parents."""
    for table in table_names:
        definition = definition.replace(f'_probe_{table}', table)
    return definition


def assert_index_names(cursor, table_names):
    cursor.execute(
        "SELECT tablename, indexname FROM pg_indexes WHERE schemaname='public' AND tablename = ANY(%s)",
        [list(table_names)],
    )
    return cursor.fetchall()
