# Deployment Guide

This document describes the deployment process after successfully completing the installation and executing the semantic interoperability pipeline described in `INSTALLATION.md`.

---

# GitHub Repository

Repository URL:

> https://github.com/aryastark1614/ANC-healthcare-data-FAIRifaction-

---

# Prerequisites

Before continuing, ensure that:

- The pipeline has executed successfully.
- Separate RDF files have been generated for both datasets.
- The CHU RDF has been uploaded to the **CHU** AllegroGraph repository.
- The Hospital RDF has been uploaded to the **Hospital** AllegroGraph repository.
- Both repositories are accessible through their SPARQL endpoints.
- The FAIR Data Point has been deployed.

---

# Deploying the RDF Repositories

## Step 1 – Create the CHU Repository

Create an AllegroGraph repository named:

```
CHU
```

---

## Step 2 – Upload the CHU RDF

Import the generated CHU RDF into the **CHU** repository.

Verify that the triples are visible after import.

---

## Step 3 – Create the Hospital Repository

Create a second AllegroGraph repository named:

```
Hospital
```

---

## Step 4 – Upload the Hospital RDF

Import the generated Hospital RDF into the **Hospital** repository.

Verify that the triples are visible after import.

---

## Step 5 – Verify the SPARQL Endpoints

Record both repository endpoints.

Example:

```
https://<server>/repositories/CHU

https://<server>/repositories/Hospital
```

These endpoints will be used for federated SPARQL queries and FAIR Data Point metadata.

---

# Publishing through the FAIR Data Point (FDP)

## Step 1 – Log in to the FDP

Access the FAIR Data Point instance.

---

## Step 2 – Create Metadata

Create the following hierarchy.

```
Catalog
    └── Dataset
            └── Distribution
```

Recommended metadata:

- Dataset title
- Description
- Creator
- Organisation
- License
- Keywords
- Version

---

## Step 3 – Register the Distributions

Register both datasets by providing:

- SPARQL endpoint
- Repository name
- Access URL
- Media type (RDF/SPARQL)

The FAIR Data Point stores metadata describing the datasets. The RDF triples remain inside AllegroGraph.

---

# Federated Querying

The interoperability framework preserves repository independence by executing federated SPARQL queries.

The CHU repository acts as the primary query endpoint and accesses the Hospital repository using the SPARQL `SERVICE` keyword.

---

# Evaluation Queries

## FR1 – Client Matching

**Run against:** CHU repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT DISTINCT ?client ?patient
WHERE {
  ?client :hasCorrespondingPatient ?patient .
}
```

---

## FR2 – Syphilis Continuity of Care (Federated)

**Run against:** CHU repository

Replace `YOUR_HOSPITAL_PASSWORD` with your Hospital repository password before execution.

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT DISTINCT ?client ?patient ?vdrlResult ?dangerSigns
WHERE {

  ?client :hasCorrespondingPatient ?patient .

  SERVICE <https://admin:YOUR_HOSPITAL_PASSWORD@YOUR_SERVER/repositories/Hospital/sparql> {

    ?patient :hasVisit ?visit .
    ?visit :hasHIVCareRecord ?hivRecord .
    ?hivRecord :hasVDRLResult ?vdrlResult .

    FILTER(LCASE(?vdrlResult)="positive")
  }

  OPTIONAL {
    ?client :hasHealthSurveillance ?surveillance .
    ?surveillance :hasDangerSigns ?dangerSigns .
  }
}
```

---

## FR3 – Referral Linkage

**Run against:** CHU repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT DISTINCT ?chuReferral ?hospitalReferral
WHERE {
  ?chuReferral :hasCorrespondingReferral ?hospitalReferral .
}
```

---

## FR4 – Pregnancy Linkage

**Run against:** CHU repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT DISTINCT ?mch ?pregnancy
WHERE {
  ?mch :hasCorrespondingPregnancy ?pregnancy .
}
```

---

## Combined Federated Query

**Run against:** CHU repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT DISTINCT ?client ?dangerSigns ?chuReferral ?hospitalReferral ?vdrlResult
WHERE {

  ?client :hasCorrespondingPatient ?patient .
  ?client :hasHealthSurveillance ?surveillance .
  ?surveillance :hasDangerSigns ?dangerSigns .

  ?client :hasClientReferral ?chuReferral .
  ?chuReferral :hasCorrespondingReferral ?hospitalReferral .

  SERVICE <https://admin:YOUR_HOSPITAL_PASSWORD@YOUR_SERVER/repositories/Hospital/sparql> {
      ?patient :hasVisit ?visit .
      ?visit :hasHIVCareRecord ?hivRecord .
      ?hivRecord :hasVDRLResult ?vdrlResult .
      FILTER(LCASE(?vdrlResult)="positive")
  }
}
```

---

## Referral Without Hospital Match

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT ?referral ?reason ?referralDate
WHERE {
  ?referral a :CHU_Referral .
  ?referral :hasReasonForReferral ?reason .
  ?referral :hasCHUReferralDate ?referralDate .

  FILTER NOT EXISTS {
    ?referral :hasCorrespondingReferral ?hospitalReferral
  }
}
```

---

## Isolation Checks

### CHU Repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT ?patient
WHERE {
  ?patient a :Patient .
}
```

### Hospital Repository

```sparql
PREFIX : <https://w3id.org/dhs/ontology#>

SELECT ?client
WHERE {
  ?client a :Client .
}
```

---

## Triple Count Validation

Run against each repository separately.

```sparql
SELECT (COUNT(*) AS ?count)
WHERE {
  ?s ?p ?o
}
```

---

# Expected Results

Successful deployment should provide:

- Independent CHU and Hospital repositories
- FAIR metadata published through the FDP
- Successful federated SPARQL execution
- Cross-system client, referral and pregnancy linkage
- Reproducible evaluation results consistent with the accompanying thesis

---

# Citation

If you use this repository in academic work, please cite the accompanying Master's thesis.
