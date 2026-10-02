---
id: platform/database
name: Primary database
kind: factual
drawer: facts
document_type: memory
scope:
  level: project
  path: './**'
observed_at: '2026-08-28T14:00:00Z'
valid_from: '2026-09-01T00:00:00Z'
valid_until: '2027-09-01T00:00:00Z'
recorded_at: '2026-09-02T12:00:00Z'
state_key: platform.primary_database
superseded_at: null
confidence: 0.8
authority: reviewed
utility: 0.7
tags: [synthetic, interop]
active_connections:
  - target_memory_id: platform/database-old
    relation_type: supersedes
  - target_memory_id: platform/database-conflict
    relation_type: conflicts_with
  - target_memory_id: platform/handbook
    relation_type: derived_from
vendor_unknown:
  preserve: yes
---
Cedar is the primary database, superseding Birch from September 2026.
