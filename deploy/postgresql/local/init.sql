DO
$$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'testtask002') THEN
    CREATE ROLE testtask002 LOGIN PASSWORD 'testtask002';
  END IF;
END;
$$;

SELECT 'CREATE DATABASE testtask002 OWNER testtask002 ENCODING ''UTF8'' LC_COLLATE ''ru_RU.UTF-8'' LC_CTYPE ''ru_RU.UTF-8'''
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'testtask002');
\gexec
