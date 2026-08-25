import os
import subprocess
import base64
import urllib.request
import urllib.error
import socket
import jaydebeapi
import traceback

from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

JAVA_HOME = os.getenv("JAVA_HOME")

if JAVA_HOME:
    os.environ["JAVA_HOME"] = JAVA_HOME
    # NOTE: fixed a pre-existing bug here — the original did
    #   JAVA_HOME + os.pathsep + "bin" + os.pathsep + PATH
    # which produces "<JAVA_HOME>:bin:<PATH>" (two broken, unusable
    # entries) instead of putting JAVA_HOME's bin directory on PATH.
    os.environ["PATH"] = os.path.join(JAVA_HOME, "bin") + os.pathsep + os.environ["PATH"]

# ============================================================
# H2 DATABASE CONFIGURATION
# ============================================================
# One shared H2 mock database still holds both CHU and hospital
# tables (Section 6.4 — this is sandbox/mock data, so a single
# local source is fine even though the two RDF outputs below are
# kept fully separate).

jdbc_driver = "org.h2.Driver"
jdbc_url = "jdbc:h2:~/maternal_test_db"
jdbc_user = "sa"
jdbc_password = ""

h2_jar_path = os.getenv("H2_JAR_PATH")

# ============================================================
# ONTOP CONFIGURATION
# ============================================================
# The ontology is shared (both sides map onto the same terms).
# The mapping file is now split in two: one drives the CHU-only
# RDF output, the other drives the hospital-only RDF output. Each
# includes its own copy of the 5 linking mappings, so both sides
# carry the same cross-system link triples independently.

ONTOP_DIR = os.getenv("ONTOP_DIR")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ontology_file = os.path.join(BASE_DIR, "CombinedOntology-2.ttl")
properties_file = os.path.join(BASE_DIR, "ontop.properties")

output_dir = os.path.join(BASE_DIR, "output")
os.makedirs(output_dir, exist_ok=True)

# Each "side" bundles everything that pipeline needs to materialise
# and upload independently: its mapping file, its RDF output path,
# and its own AllegroGraph repository credentials/endpoint.
SIDES = {
    "CHU": {
        "mapping_file": os.path.join(BASE_DIR, "chu-mapping.ttl"),
        "rdf_output_file": os.path.join(output_dir, "chu_output.rdf"),
        "ag_user": os.getenv("AG_USER_CHU"),
        "ag_password": os.getenv("AG_PASSWORD_CHU"),
        "ag_base_url": os.getenv("AG_BASE_URL_CHU"),
        "ag_repo": os.getenv("AG_REPO_CHU"),
    },
    "Hospital": {
        "mapping_file": os.path.join(BASE_DIR, "hospital-mapping.ttl"),
        "rdf_output_file": os.path.join(output_dir, "hospital_output.rdf"),
        "ag_user": os.getenv("AG_USER_HOSPITAL"),
        "ag_password": os.getenv("AG_PASSWORD_HOSPITAL"),
        "ag_base_url": os.getenv("AG_BASE_URL_HOSPITAL"),
        "ag_repo": os.getenv("AG_REPO_HOSPITAL"),
    },
}

# ============================================================
# STRIP FOREIGN-SIDE TYPE INFERENCE
# ============================================================
CHU_PREFIXES = (
    "https://w3id.org/dhs/ontology#Client_",
    "https://w3id.org/dhs/ontology#CommunityHealthUnit_",
    "https://w3id.org/dhs/ontology#HouseholdRegistration_",
    "https://w3id.org/dhs/ontology#HealthSurveillance_",
    "https://w3id.org/dhs/ontology#CHU_Referral_",
    "https://w3id.org/dhs/ontology#MaternalChildHealth_",
    "https://w3id.org/dhs/ontology#ServiceDelivery_",
    "https://w3id.org/dhs/ontology#EnvironmentalWASH_",
)
HOSPITAL_PREFIXES=(
    "https://w3id.org/dhs/ontology#Facility_",
    "https://w3id.org/dhs/ontology#Patient_",
    "https://w3id.org/dhs/ontology#MaternalProfile_",
    "https://w3id.org/dhs/ontology#HIVCareRecord_",
    "https://w3id.org/dhs/ontology#Referral_",
    "https://w3id.org/dhs/ontology#Visit_",
)

LINK_PREDICATES = {
    "https://w3id.org/dhs/ontology#hasCorrespondingPatient",
    "https://w3id.org/dhs/ontology#hasCorrespondingPregnancy",
    "https://w3id.org/dhs/ontology#hasCorrespondingReferral",
    "https://w3id.org/dhs/ontology#hasCorrespondingSyphilisRecord",
    "https://w3id.org/dhs/ontology#referredToFacility",
}

def strip_foreign_type_inference(rdf_file, foreign_prefixes, label):
    """
    Remove inferred triples whose SUBJECT is a foreign-side URI,
    EXCEPT the deliberate cross-system linking predicates.
    """
    from rdflib import Graph, URIRef

    g = Graph()
    g.parse(rdf_file, format="xml")
    before = len(g)

    to_remove = []

    for s, p, o in g:
        if not isinstance(s, URIRef):
            continue

        if any(str(s).startswith(prefix) for prefix in foreign_prefixes):
            if str(p) not in LINK_PREDICATES:
                to_remove.append((s, p, o))

    for triple in to_remove:
        g.remove(triple)

    g.serialize(destination=rdf_file, format="xml")

    print(
        f"[{label}] Stripped {before-len(g)} foreign-side inferred "
        f"triple(s) ({before} -> {len(g)})."
    )

for label, cfg in SIDES.items():
    missing = [k for k in ("ag_user", "ag_password", "ag_base_url", "ag_repo") if not cfg[k]]
    if missing:
        raise RuntimeError(
            f"[CONFIG ERROR] Missing env vars for {label} side: "
            f"{[f'{k.upper()}_{label.upper()}' for k in missing]}. "
            f"Check your .env file."
        )
    cfg["endpoint_url"] = f"{cfg['ag_base_url'].rstrip('/')}/repositories/{cfg['ag_repo']}/statements"

print("\n=== ALLEGROGRAPH SETTINGS ===")
for label, cfg in SIDES.items():
    print(f"[{label}] USER={cfg['ag_user']}  BASE_URL={cfg['ag_base_url']}  "
          f"REPO={cfg['ag_repo']}  ENDPOINT={cfg['endpoint_url']}")

# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_h2_connection():
    return jaydebeapi.connect(
        jdbc_driver,
        jdbc_url,
        [jdbc_user, jdbc_password],
        h2_jar_path
    )

# ============================================================
# CHECK DATABASE TABLES
# ============================================================
# Unchanged — still a single check against the one shared H2
# source, since both mapping files read from the same mock tables.

def check_tables():
    try:
        conn = get_h2_connection()
        cursor = conn.cursor()

        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()

        print("\n=== DATABASE TABLES ===")

        for table in tables:
            print(table[0])

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] check_tables(): {e}")
        return False

# ============================================================
# VALIDATE DATA
# ============================================================

def validate_data():
    try:
        conn = get_h2_connection()
        cursor = conn.cursor()

        print("\n=== VALIDATING DATA ===")

        validation_queries = {
            "Clients": "SELECT COUNT(*) FROM CLIENT",
            "ANC Clients": "SELECT COUNT(*) FROM ANC_CLIENT",
            "ANC Visits": "SELECT COUNT(*) FROM ANC_VISIT",
            "Pregnancy Details": "SELECT COUNT(*) FROM PREGNANCY_DETAILS",
            "Laboratory Results": "SELECT COUNT(*) FROM LABORATORY_RESULTS",
            "HIV Screening": "SELECT COUNT(*) FROM HIV_SCREENING",
            "Treatments": "SELECT COUNT(*) FROM TREATMENT_AND_PREVENTION",
            "Hospital Referrals": "SELECT COUNT(*) FROM HOSPITAL_REFERRAL",
            "Community Referrals": "SELECT COUNT(*) FROM REFERRAL"
        }

        for label, query in validation_queries.items():
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"{label}: {count}")

        conn.close()
        return True

    except Exception as e:
        print(f"[ERROR] validate_data(): {e}")
        return False

# ============================================================
# RUN ONTOP MATERIALIZATION
# ============================================================
# Parameterised so it can be called once per side, each with its
# own mapping file and output path.

def run_ontop_materialization(mapping_file, rdf_output_file, label):
    try:
        print(f"\n=== RUNNING ONTOP MATERIALIZATION [{label}] ===")

        command = ["./ontop",
            "materialize",
            "-m", mapping_file,
            "-t", ontology_file,
            "-p", properties_file,
            "-o", rdf_output_file
        ]

        result = subprocess.run(
            command,
            cwd=ONTOP_DIR,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        print(result.stdout)

        if result.returncode != 0:
            print(result.stderr)
            print(f"[ERROR] Ontop materialization failed for {label}.")
            return False

        print(f"[SUCCESS] RDF materialization completed for {label}.")
        return True

    except Exception as e:
        print(f"[ERROR] run_ontop_materialization({label}): {e}")
        return False

# ============================================================
# UPLOAD RDF TO ALLEGROGRAPH
# ============================================================
# Parameterised the same way — one call per side, targeting that
# side's own repository with its own credentials.

def upload_rdf_to_allegrograph(rdf_output_file, endpoint_url, ag_user, ag_password, label, timeout_seconds=60):
    try:
        print(f"\n=== UPLOADING RDF TO ALLEGROGRAPH [{label}] ===")

        with open(rdf_output_file, "rb") as rdf_file:
            rdf_data = rdf_file.read()

        headers = {
            "Content-Type": "application/rdf+xml",
            "Authorization": "Basic " + base64.b64encode(
                f"{ag_user}:{ag_password}".encode()
            ).decode()
        }

        request = urllib.request.Request(
            url=endpoint_url,
            data=rdf_data,
            headers=headers,
            method="POST"
        )

        response = urllib.request.urlopen(request, timeout=timeout_seconds)

        print(f"[{label}] Upload Status: {response.status}")

        body = response.read().decode("utf-8", errors="ignore")
        print(body)

        if response.status in [200, 201, 204]:
            print(f"[SUCCESS] RDF uploaded successfully for {label}.")
            return True

        return False

    except urllib.error.HTTPError as e:
        # NOTE: the original file had this same except clause repeated
        # three times in a row — only the first one could ever fire, the
        # other two were dead code. Collapsed to one.
        print(f"[HTTP ERROR][{label}] {e.code} - {e.reason}")
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
        return False

    except socket.timeout:
        print(f"[TIMEOUT ERROR][{label}] Upload timed out.")
        return False

    except Exception:
        print(f"[ERROR][{label}] Unexpected failure during upload:")
        traceback.print_exc()
        return False

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():

    print("\n========================================")
    print("MATERNAL HEALTHCARE SEMANTIC PIPELINE")
    print("Two-repository mode: CHU + Hospital")
    print("========================================")

    if not check_tables():
        return

    if not validate_data():
        return

    # Materialise and upload each side independently. One side
    # failing should not silently prevent the other from completing —
    # KCEI's deployment and Pumwani's deployment are meant to be
    # genuinely independent, so their success/failure is tracked
    # and reported separately rather than the whole pipeline
    # aborting on the first problem.
    results = {}

    for label, cfg in SIDES.items():
        materialised = run_ontop_materialization(
            cfg["mapping_file"], cfg["rdf_output_file"], label
        )
        if not materialised:
            results[label] = "MATERIALIZATION FAILED"
            continue

        foreign = HOSPITAL_PREFIXES if label == "CHU" else CHU_PREFIXES
        strip_foreign_type_inference(
            cfg["rdf_output_file"],
            foreign,
            label,
        )

        uploaded = upload_rdf_to_allegrograph(
            cfg["rdf_output_file"],
            cfg["endpoint_url"],
            cfg["ag_user"],
            cfg["ag_password"],
            label,
        )
        results[label] = "SUCCESS" if uploaded else "UPLOAD FAILED"

    print("\n========================================")
    print("PIPELINE SUMMARY")
    for label, status in results.items():
        print(f"  {label}: {status}")
    print("========================================")

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()