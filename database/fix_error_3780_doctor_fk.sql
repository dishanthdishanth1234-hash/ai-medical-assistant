-- Fix MySQL ERROR 3780 (HY000): doctor_id vs doctors.id incompatible for fk_appt_doctor.
--
-- Typical cause: `doctors` was created first by SQLAlchemy with a **signed** `INT` primary key,
-- while `appointments.doctor_id` is defined as **INT UNSIGNED** in migration_v2.sql / schema.sql.
--
-- Step 1 — run this (safe if `doctors` is already UNSIGNED):
--   mysql -u root -p medical_assistant < database/fix_error_3780_doctor_fk.sql
--
-- Step 2 — if `appointments` was NOT created, run the `CREATE TABLE appointments` block from
--   `database/migration_v2.sql` again (or full migration if you prefer).

USE medical_assistant;

ALTER TABLE doctors
  MODIFY COLUMN id INT UNSIGNED NOT NULL AUTO_INCREMENT;
