Update NocoDB row with public URL and status.

Dependencies: managed with uv via pyproject.toml.

Inputs:
- record_id
- table_id
- public_mp4_url
Outputs:
- updated record

Behavior:
- Uses `PATCH /api/v2/tables/{tableId}/records`.
- Updates only `chengpinurl` for the given `Id`.
- `tableId` is taken from message payload at runtime.
- `S8_NOCODB_TABLE_ID` can be used as fallback when older/partial messages do not include `table_id`.
