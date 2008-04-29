BEGIN;


CREATE OR REPLACE FUNCTION cciw_upgrade_to_schema_4() RETURNS integer AS $PROC$
DECLARE version varchar(255) NOT NULL = '';
BEGIN
        version :=  value FROM cciwmain_metainfo WHERE key = 'schema_version';
        IF version <> '3' THEN
                RAISE EXCEPTION 'Incorrect schema version';
        END IF;

	CREATE TABLE "utils_confirmtoken" (
	    "id" serial NOT NULL PRIMARY KEY,
	    "action_type" varchar(50) NOT NULL,
	    "token" varchar(10) NOT NULL,
	    "expires" timestamp with time zone NOT NULL,
	    "objdata" text NOT NULL
	);

	CREATE TABLE "officers_reference" (
	    "id" serial NOT NULL PRIMARY KEY,
	    "application_id" integer NOT NULL REFERENCES "officers_application" ("id") DEFERRABLE INITIALLY DEFERRED,
	    "referee_number" smallint NOT NULL,
	    UNIQUE ("application_id", "referee_number")
	);

        UPDATE cciwmain_metainfo SET value = '4' WHERE key = 'schema_version';

        RETURN 4;
END;

$PROC$ LANGUAGE plpgsql;

SELECT cciw_upgrade_to_schema_4();

COMMIT;
