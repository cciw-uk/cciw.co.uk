BEGIN;


CREATE OR REPLACE FUNCTION cciw_upgrade_to_schema_5() RETURNS integer AS $PROC$
DECLARE version varchar(255) NOT NULL = '';
BEGIN
        version :=  value FROM cciwmain_metainfo WHERE key = 'schema_version';
        IF version <> '4' THEN
                RAISE EXCEPTION 'Incorrect schema version';
        END IF;


	CREATE TABLE "officers_invitation" (
	    "id" serial NOT NULL PRIMARY KEY,
	    "officer_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
	    "camp_id" integer NOT NULL REFERENCES "cciwmain_camp" ("id") DEFERRABLE INITIALLY DEFERRED,
	    UNIQUE ("officer_id", "camp_id")
	);

	ALTER TABLE "officers_reference" ADD COLUMN "requested" boolean NOT NULL;
	ALTER TABLE "officers_reference" ADD COLUMN "received" boolean NOT NULL;
	ALTER TABLE "officers_reference" ADD COLUMN "comments" text NOT NULL;

        UPDATE cciwmain_metainfo SET value = '5' WHERE key = 'schema_version';

        RETURN 5;
END;

$PROC$ LANGUAGE plpgsql;

SELECT cciw_upgrade_to_schema_5();

COMMIT;
