# Architecture

The MVP separates source retrieval, reproducible snapshots, deterministic transformations, and
decision presentation. This keeps the user-facing product available even when a government API
is slow or changes.

```mermaid
flowchart TB
  subgraph Sources["Public aggregate sources"]
    CDC["CDC PLACES 2025"]
    CMS["CMS Hospital General Information"]
    ACS["Census ACS 2024 · optional key"]
  end
  subgraph DataPlane["Data plane"]
    API["Requests-based API adapters"]
    RAW["Raw / API payloads · gitignored"]
    SNAP["Curated versioned snapshots"]
    MART["Gold county priority mart"]
  end
  subgraph Controls["Control plane"]
    CONTRACT["Data contracts"]
    TESTS["Unit + quality tests"]
    MANIFEST["Build manifest"]
    CICD["GitHub Actions"]
  end
  subgraph Product["Decision product"]
    DASH["Executive dashboard"]
    MAP["Priority map + profile"]
    SIM["Resource simulator"]
    TRUST["Trust center"]
  end
  CDC --> API
  CMS --> API
  ACS -.-> API
  API --> RAW --> SNAP --> MART
  CONTRACT -.-> API
  TESTS -.-> MART
  MANIFEST -.-> MART
  CICD -.-> API
  MART --> DASH
  DASH --> MAP
  DASH --> SIM
  DASH --> TRUST
```

## Deployment boundary

Local and CI runs use committed snapshots. Terraform provides an opt-in S3/KMS/CloudWatch
foundation. Compute deployment is deliberately excluded from automatic CI until costs,
authentication, network boundaries, and an AWS account are approved.
