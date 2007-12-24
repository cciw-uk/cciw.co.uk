BEGIN TRANSACTION;

-- This will produce error immediately if table already exists,
-- which it shouldn't before this upgrade.
CREATE TABLE cciwmain_metainfo (
       key varchar(255) NOT NULL,
       value varchar(255) NOT NULL
);


/* Convert Person.user (foreign key) to Person.users (many to manyy) */
CREATE TABLE cciwmain_person_to_user_temp (
       person_id int4 REFERENCES cciwmain_person (id),
       user_id int4 REFERENCES auth_user (id)
);

INSERT INTO cciwmain_person_to_user_temp (person_id, user_id) SELECT id, user_id FROM cciwmain_person WHERE user_id IS NOT NULL;
       
ALTER TABLE cciwmain_person DROP CONSTRAINT "cciwmain_person_user_id_fkey";
ALTER TABLE cciwmain_person DROP COLUMN "user_id";

-- The following definition is from django-admin.py sqlall 
CREATE TABLE "cciwmain_person_users" (
    "id" serial NOT NULL PRIMARY KEY,
    "person_id" integer NOT NULL REFERENCES "cciwmain_person" ("id") DEFERRABLE INITIALLY DEFERRED,
    "user_id" integer NOT NULL REFERENCES "auth_user" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("person_id", "user_id")
);

INSERT INTO cciwmain_person_users (person_id, user_id) SELECT person_id, user_id FROM cciwmain_person_to_user_temp;

DROP TABLE cciwmain_person_to_user_temp;

-- Update schema once successful.
INSERT INTO cciwmain_metainfo (key, value) VALUES ('schema_version', '2');


COMMIT TRANSACTION;

