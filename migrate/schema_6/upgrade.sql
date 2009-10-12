BEGIN;


CREATE OR REPLACE FUNCTION cciw_upgrade_to_schema_6() RETURNS integer AS $PROC$
DECLARE version varchar(255) NOT NULL = '';
BEGIN
        version :=  value FROM cciwmain_metainfo WHERE key = 'schema_version';
        IF version <> '5' THEN
                RAISE EXCEPTION 'Incorrect schema version';
        END IF;

        CREATE TABLE "officers_referenceform" (
            "id" serial NOT NULL PRIMARY KEY,
            "referee_name" varchar(100) NOT NULL,
            "how_long_known" varchar(150) NOT NULL,
            "capacity_known" text NOT NULL,
            "known_offences" boolean NOT NULL,
            "known_offences_details" text NOT NULL,
            "capability_children" text NOT NULL,
            "character" text NOT NULL,
            "concerns" text NOT NULL,
            "comments" text NOT NULL,
            "date_created" date NOT NULL,
            "reference_info_id" integer NOT NULL REFERENCES "officers_reference" ("id") DEFERRABLE INITIALLY DEFERRED
        );
        CREATE INDEX "officers_referenceform_reference_info_id" ON "officers_referenceform" ("reference_info_id");


        UPDATE cciwmain_metainfo SET value = '6' WHERE key = 'schema_version';

        RETURN 6;
END;

$PROC$ LANGUAGE plpgsql;

SELECT cciw_upgrade_to_schema_6();

COMMIT;
