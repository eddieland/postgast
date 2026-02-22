## ADDED Requirements

### Requirement: to_drop is exported from the postgast package

`to_drop` SHALL be importable directly from the `postgast` package (i.e., `from postgast import to_drop`).

#### Scenario: Direct import

- **WHEN** a user writes `from postgast import to_drop`
- **THEN** the import SHALL succeed without errors
