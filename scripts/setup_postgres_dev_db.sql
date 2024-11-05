
DO
$do$
BEGIN
   IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE  rolname = 'cciw_dev') THEN
      RAISE NOTICE 'Role "cciw_dev" already exists. Skipping.';
   ELSE
      CREATE USER cciw_dev WITH PASSWORD 'cciw_dev';
   END IF;
END
$do$;

GRANT ALL ON DATABASE cciw_dev TO cciw_dev;
ALTER USER cciw_dev CREATEDB;
ALTER DATABASE cciw_dev OWNER to cciw_dev;
