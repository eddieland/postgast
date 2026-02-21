## MODIFIED Requirements

### Requirement: All helpers accept any protobuf Message as input

All helper functions (`extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`) SHALL accept any `google.protobuf.message.Message` instance as input, including
`ParseResult`, individual statement nodes (e.g., `SelectStmt`), or any subtree node.

#### Scenario: Works on ParseResult

- **WHEN** any helper is called with the `ParseResult` returned by `postgast.parse()`
- **THEN** it SHALL traverse the entire parse tree and return results

#### Scenario: Works on a subtree node

- **WHEN** any helper is called with a `SelectStmt` extracted from a `ParseResult`
- **THEN** it SHALL traverse only that subtree and return results from within it

### Requirement: All helpers are exported from the postgast package

`find_nodes`, `extract_tables`, `extract_columns`, `extract_functions`, `extract_function_identity`,
`extract_trigger_identity`, `FunctionIdentity`, and `TriggerIdentity` SHALL be importable directly from the `postgast`
package (i.e., `from postgast import extract_function_identity`).

#### Scenario: Direct import

- **WHEN** a user writes
  `from postgast import extract_function_identity, extract_trigger_identity, FunctionIdentity, TriggerIdentity`
- **THEN** the import SHALL succeed without errors
