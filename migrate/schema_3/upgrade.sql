BEGIN;

-- Assert that we are at version 2


CREATE OR REPLACE FUNCTION cciw_upgrade_to_schema_3() RETURNS integer AS $PROC$
DECLARE version varchar(255) NOT NULL = '';
BEGIN
	version :=  value FROM cciwmain_metainfo WHERE key = 'schema_version';
	IF version <> '2' THEN
		RAISE EXCEPTION 'Incorrect schema version';
	END IF;

	CREATE TABLE "cciwmain_camp_admins" (
	    "id" serial NOT NULL PRIMARY KEY,
	    "camp_id" integer NOT NULL REFERENCES "cciwmain_camp" ("id") DEFERRABLE INITIALLY DEFERRED,
	    "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
	    UNIQUE ("camp_id", "user_id")
	);

	UPDATE cciwmain_metainfo SET value = '3' WHERE key = 'schema_version';

	RETURN 3;
END;

$PROC$ LANGUAGE plpgsql;

SELECT cciw_upgrade_to_schema_3();

COMMIT;
