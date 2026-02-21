## 1. Library Loading

- [x] 1.1 Create `src/postgast/_native.py` with platform-aware library loading using `ctypes.util.find_library` and
  `ctypes.CDLL`
- [x] 1.2 Raise a descriptive `OSError` if the library cannot be found

## 2. Struct Definitions

- [x] 2.1 Define `PgQueryError` ctypes Structure (message, funcname, filename, lineno, cursorpos, context)
- [x] 2.2 Define `PgQueryProtobuf` ctypes Structure (len, data)
- [x] 2.3 Define result structs: `PgQueryParseResult`, `PgQueryProtobufParseResult`, `PgQueryNormalizeResult`,
  `PgQueryFingerprintResult`, `PgQueryScanResult`, `PgQuerySplitResult`, `PgQueryDeparseResult`

## 3. Function Signatures

- [x] 3.1 Declare argtypes/restype for core functions: `pg_query_parse`, `pg_query_parse_protobuf`,
  `pg_query_normalize`, `pg_query_fingerprint`, `pg_query_scan`, `pg_query_split_with_scanner`,
  `pg_query_deparse_protobuf`
- [x] 3.2 Declare argtypes/restype for free functions: `pg_query_free_parse_result`,
  `pg_query_free_protobuf_parse_result`, `pg_query_free_normalize_result`, `pg_query_free_fingerprint_result`,
  `pg_query_free_scan_result`, `pg_query_free_split_result`, `pg_query_free_deparse_result`

## 4. Verify

- [x] 4.1 Run linting and type-checking (`make lint`)
