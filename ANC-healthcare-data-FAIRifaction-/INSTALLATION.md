# Installation Guide

This document explains how to reproduce the semantic interoperability framework presented in the accompanying Master's thesis.

The framework integrates maternal healthcare data from Community Health Units (CHUs) and healthcare facilities using Semantic Web technologies. It uses H2 relational databases as the data source, Ontop for ontology-based data access (OBDA), AllegroGraph as the RDF triple store, and a FAIR Data Point (FDP) for publishing FAIR metadata.

The implementation generates separate RDF knowledge graphs for the CHU and Hospital datasets, which remain independently managed and are integrated at query time using federated SPARQL.

---

# 1. Software Requirements

Before running the project, install the following software.

| Software | Recommended Version |
|----------|---------------------|
| Java JDK | 21 |
| Python | 3.11 or later |
| H2 Database | 2.4.240 |
| Ontop CLI | Latest Stable Release |
| Protégé | 5.6 or later |
| AllegroGraph | Cloud or Local Instance |
| Docker | Latest |
| Docker Compose | Latest |

---

# 2. Clone the Repository

Clone the GitHub repository.

```bash
git clone https://github.com/<username>/ANC-healthcare-data-FAIRification.git

cd ANC-healthcare-data-FAIRification
```

---

# 3. Create a Python Virtual Environment (Recommended)

```bash
python3 -m venv .venv
```

Activate the environment.

### macOS / Linux

```bash
source .venv/bin/activate
```

### Windows

```cmd
.venv\Scripts\activate
```

---

# 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

# 5. Install Java

Install Java Development Kit (JDK 21).

Verify the installation.

```bash
java -version
```

After installation, note the installation directory, as it will be required when configuring the environment variables.

---

# 6. Install H2 Database

Download H2 Database from:

https://www.h2database.com

Place the H2 JAR file inside:

```
h2/
    h2-2.4.240.jar
```

---

# 7. Create the H2 Database

Open the H2 Console and create a database named:

```
maternal_test_db
```

Connection settings:

```
Driver Class:
org.h2.Driver

JDBC URL:
jdbc:h2:~/maternal_test_db

User:
sa

Password:
(leave blank)
```

---

# 8. Create the Database Tables

Execute the SQL schema supplied with the repository.

```
database/schema.sql
```

This creates both the Community Health Unit and Hospital tables used by the interoperability framework.

---

# 9. Populate the Database

Execute the supplied sample dataset.

```
database/sample_dataset.sql
```

---

# 10. Install Ontop

Download Ontop from:

https://ontop-vkg.org

Extract it into:

```
ontop/
```

---

# 11. Configure Ontop

Create:

```
ontology/ontop.properties
```

Example configuration:

```properties
jdbc.url=jdbc:h2:~/maternal_test_db
jdbc.user=sa
jdbc.password=
jdbc.driver=org.h2.Driver
```

---

# 12. Configure Environment Variables

Copy the example configuration.

```bash
cp .env.example .env
```

Edit `.env` and replace the placeholder values with your local configuration.

Required variables include:

```
JAVA_HOME
H2_JAR_PATH
ONTOP_DIR

AG_USER_CHU
AG_PASSWORD_CHU
AG_BASE_URL_CHU
AG_REPO_CHU

AG_USER_HOSPITAL
AG_PASSWORD_HOSPITAL
AG_BASE_URL_HOSPITAL
AG_REPO_HOSPITAL
```

Do **not** commit the `.env` file to GitHub.

---

# 13. Create the AllegroGraph Repositories

Create two repositories:

```
CHU
```

and

```
Hospital
```

These names must match the values configured in `.env`.

---

# 14. Verify the Ontology

Open:

```
ontology/CombinedOntology-2.ttl
```

using Protégé.

---

# 15. Verify the R2RML Mapping

Verify:

```
ontology/CombinedOntology-2-mapping.ttl
```

No modifications are required unless the relational schema changes.

---

# 16. Run the Pipeline

Execute:

```bash
python main_pipeline.py
```

The pipeline:

1. Connects to the H2 database.
2. Validates the data.
3. Executes Ontop materialization.
4. Generates CHU RDF.
5. Generates Hospital RDF.
6. Uploads both RDF graphs to AllegroGraph.

---

# 17. Deploy the FAIR Data Point

Navigate to the FAIR Data Point directory.

```bash
cd FAIRDataPoint
```

Start the services.

```bash
docker compose up -d
```

Open:

```
http://localhost
```

Create:

```
Catalog
    Dataset
        Distribution
```

Register the CHU and Hospital SPARQL endpoints.

---

# 18. Verify Successful Execution

Successful execution should report:

- Database connection established
- RDF materialization completed
- CHU RDF uploaded successfully
- Hospital RDF uploaded successfully

---

# 19. Project Workflow

```text
CHU Database
      │
      ▼
 Ontop Mapping
      │
      ▼
   CHU RDF
      │
      ▼
CHU AllegroGraph Repository
      │
      │  SERVICE
      ▼
Hospital AllegroGraph Repository
      ▲
      │
 Hospital RDF
      ▲
 Ontop Mapping
      ▲
Hospital Database

      │
      ▼
FAIR Data Point
```

---

# Troubleshooting

### Java cannot be found

Verify `JAVA_HOME` is configured correctly.

### Ontop cannot connect

Verify the JDBC URL and `ontology/ontop.properties`.

### RDF generation fails

Verify the ontology, mappings, Ontop installation, and populated database.

### AllegroGraph upload fails

Verify repository names, endpoint URLs, usernames, and passwords.

### Federated queries return no results

Verify both repositories are populated and the `SERVICE` endpoint is correct.

---

# Citation

If you use this repository for academic work, please cite the accompanying Master's thesis.
