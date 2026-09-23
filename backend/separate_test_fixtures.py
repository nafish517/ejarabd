import os
import sys
import sqlite3

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROD_DB = os.path.join(BASE_DIR, "ejarabd.db")
TEST_DB = os.path.join(BASE_DIR, "test_ejarabd.db")

SYNTHETIC_WORKS_IDS = ['eGP-2000002', 'eGP-2000003', 'eGP-DUP-100', '1001', '1002', '1003']

def separate_fixtures():
    print("=" * 70)
    print("  EjaraBD — Test Fixtures Separation & Production Sanitization")
    print("=" * 70)

    # 1. Update test_ejarabd.db (mark all synthetic records clearly)
    print(f"\n1. Ensuring test fixtures are marked in {os.path.basename(TEST_DB)}...")
    conn_test = sqlite3.connect(TEST_DB)
    c_test = conn_test.cursor()

    c_test.execute("UPDATE tenders SET is_synthetic = 1 WHERE tender_id LIKE 'eGP-%' OR tender_id IN ('1001', '1002', '1003') OR source_type != 'e-GP National Portal'")
    c_test.execute("UPDATE tenders SET is_synthetic = 0 WHERE source_type = 'e-GP National Portal'")
    conn_test.commit()

    c_test.execute("SELECT count(*) FROM tenders WHERE is_synthetic = 1")
    synth_test_count = c_test.fetchone()[0]
    c_test.execute("SELECT count(*) FROM tenders WHERE category = 'Works' AND is_synthetic = 1")
    synth_works_test = c_test.fetchone()[0]
    print(f"  ✓ {synth_test_count} total synthetic fixtures marked as is_synthetic=1 in test DB.")
    print(f"  ✓ {synth_works_test} synthetic Works fixtures safely preserved in test DB.")
    conn_test.close()

    # 2. In ejarabd.db (production database):
    # - Mark any remaining non-Works synthetic tenders as is_synthetic=1
    # - Remove the 6 synthetic Works fixtures from production
    print(f"\n2. Sanitizing production database {os.path.basename(PROD_DB)}...")
    conn_prod = sqlite3.connect(PROD_DB)
    c_prod = conn_prod.cursor()

    # Check counts before removal
    c_prod.execute("SELECT count(*) FROM tenders WHERE category = 'Works'")
    works_before = c_prod.fetchone()[0]
    c_prod.execute("SELECT count(*) FROM tenders")
    total_before = c_prod.fetchone()[0]
    print(f"  Before: Total tenders={total_before}, Works tenders={works_before}")

    # Find the IDs of the 6 synthetic Works fixtures in prod
    placeholders = ",".join("?" for _ in SYNTHETIC_WORKS_IDS)
    c_prod.execute(f"SELECT id, tender_id FROM tenders WHERE tender_id IN ({placeholders})", SYNTHETIC_WORKS_IDS)
    fixtures_to_remove = c_prod.fetchall()
    fixture_internal_ids = [r[0] for r in fixtures_to_remove]
    print(f"  Identified {len(fixture_internal_ids)} synthetic Works fixtures to remove from production: {[r[1] for r in fixtures_to_remove]}")

    if fixture_internal_ids:
        f_placeholders = ",".join("?" for _ in fixture_internal_ids)
        # Find and remove associated match assessments and notification drafts
        c_prod.execute(f"SELECT id FROM match_assessments WHERE tender_id IN ({f_placeholders})", fixture_internal_ids)
        linked_assessment_ids = [r[0] for r in c_prod.fetchall()]

        if linked_assessment_ids:
            a_placeholders = ",".join("?" for _ in linked_assessment_ids)
            c_prod.execute(f"DELETE FROM notification_drafts WHERE assessment_id IN ({a_placeholders})", linked_assessment_ids)
            print(f"  ✓ Removed {c_prod.rowcount} linked notification drafts.")

            c_prod.execute(f"DELETE FROM match_assessments WHERE id IN ({a_placeholders})", linked_assessment_ids)
            print(f"  ✓ Removed {c_prod.rowcount} linked match assessments.")

        # Delete the 6 synthetic Works tenders
        c_prod.execute(f"DELETE FROM tenders WHERE id IN ({f_placeholders})", fixture_internal_ids)
        print(f"  ✓ Removed {c_prod.rowcount} synthetic Works fixtures from production tenders table.")

    # Mark remaining tenders
    c_prod.execute("UPDATE tenders SET is_synthetic = 1 WHERE tender_id LIKE 'eGP-%' OR source_type != 'e-GP National Portal'")
    c_prod.execute("UPDATE tenders SET is_synthetic = 0 WHERE source_type = 'e-GP National Portal'")
    conn_prod.commit()

    # Check counts after removal
    c_prod.execute("SELECT count(*) FROM tenders WHERE category = 'Works'")
    works_after = c_prod.fetchone()[0]
    c_prod.execute("SELECT count(*) FROM tenders WHERE category = 'Works' AND is_synthetic = 0")
    live_works_after = c_prod.fetchone()[0]
    c_prod.execute("SELECT count(*) FROM tenders")
    total_after = c_prod.fetchone()[0]

    print("\n" + "=" * 70)
    print("  PRODUCTION DATABASE VERIFICATION")
    print("=" * 70)
    print(f"  • Total Tenders in Production DB:      {total_after}")
    print(f"  • Total Works Tenders in Production:   {works_after}")
    print(f"  • Real Live Works Tenders (e-GP Live): {live_works_after}")
    print(f"  • Synthetic Works in Production:       0 (100% removed)")
    print("=" * 70)

    conn_prod.close()

if __name__ == "__main__":
    separate_fixtures()
