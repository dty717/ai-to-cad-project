# Fusion MCP Studio: MCP handshake and tool discovery

This document records the JSON-RPC initialization and `tools/list` exchange for the **MCP Server Adapter** used by FusionStudio.

## 1. Initialize the session

### Request (`req1`)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "FusionStudio",
      "version": "1.0.0"
    }
  }
}
```

### Response (`res1`)

```json
{
  "id": 1,
  "jsonrpc": "2.0",
  "result": {
    "capabilities": {
      "resources": {
        "listChanged": false,
        "subscribe": false
      },
      "tools": {
        "listChanged": false
      }
    },
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "MCP Server Adapter",
      "version": "1.0.0"
    }
  }
}
```

The response confirms protocol `2024-11-05`, advertises no resource subscriptions or list-change notifications, and identifies the server as **MCP Server Adapter 1.0.0**.

## 2. Discover available tools

### Request (`req2`)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}
```

### Response (`res2`)

The response contains four tools:

| Tool | Purpose |
| --- | --- |
| `fusion_mcp_electronics_read` | Reads Fusion Electronics schematic, board, library, and related design entities. |
| `fusion_mcp_execute` | Executes operations in the active Fusion model. |
| `fusion_mcp_read` | Reads geometry, documents, projects, licensing, API documentation, screenshots, and active command state. |
| `fusion_mcp_update` | Undoes or redoes operations in the active document. |

### `fusion_mcp_electronics_read`

**Required parameter:** `entity_type`

**Optional parameter:** `object`, containing:

- `fields`: property names to return; omit it to return all columns.
- `filters`: predicates with `property`, `op`, and `value`.
- `pagination`: `limit` and `offset`; the default limit is 100 and the limit may not exceed 1000.

Filter operators are `eq` for string properties and `lt` or `gt` only for numeric/integer properties that expose those operators in the per-class schema resource.

Supported `entity_type` values:

`electronics.Attribute`, `electronics.Board`, `electronics.Bus`, `electronics.Circle`, `electronics.Contact`, `electronics.ContactRef`, `electronics.Device`, `electronics.DeviceSet`, `electronics.Dimension`, `electronics.Element`, `electronics.Error`, `electronics.Frame`, `electronics.Gate`, `electronics.Grid`, `electronics.Hole`, `electronics.Instance`, `electronics.Junction`, `electronics.Label`, `electronics.Layer`, `electronics.Library`, `electronics.Module`, `electronics.ModuleInstance`, `electronics.Net`, `electronics.NetClass`, `electronics.Package`, `electronics.Package3D`, `electronics.Pad`, `electronics.Part`, `electronics.Pin`, `electronics.PinRef`, `electronics.PolyCutout`, `electronics.PolyPour`, `electronics.PolyShape`, `electronics.Port`, `electronics.PortNetMappingEntry`, `electronics.PortRef`, `electronics.Rectangle`, `electronics.Schematic`, `electronics.Segment`, `electronics.Sheet`, `electronics.Signal`, `electronics.Smd`, `electronics.Spline`, `electronics.Symbol`, `electronics.Technology`, `electronics.Text`, `electronics.Variant`, `electronics.VariantDef`, `electronics.Via`, and `electronics.Wire`.

Discovery resources are:

- `resource://mcp.electronics_entity_types` — all types and active-workspace hints.
- `resource://mcp.electronics_schema_<class>` — properties and filter operators for a type.

Example query:

```json
{
  "entity_type": "electronics.Net",
  "object": {
    "fields": ["name"],
    "filters": [
      {
        "property": "name",
        "op": "eq",
        "value": "GND"
      }
    ],
    "pagination": {
      "limit": 100,
      "offset": 0
    }
  }
}
```

Use `pagination.nextOffset` from the response when `pagination.hasMore` is true.

### `fusion_mcp_execute`

**Required parameter:** `featureType`

**Object parameter:** `object`, whose fields depend on the operation.

Supported `featureType` values:

| Feature type | Operation |
| --- | --- |
| `script` | Executes Python in the active Fusion design. |
| `document` | Opens, closes, or saves a document. |
| `purchase` | Opens a relevant in-app purchase/licensing manager tab. |
| `editImage` | Generates a picture-only preview or places the model in a described environment. |
| `generatePowerpoint` | Generates a PowerPoint from JSON slide definitions. |
| `previewImage` | Previews, externally opens, or downloads generated images and presentations. |

#### Scripts

Scripts require `featureType="script"` and an `object` containing `script`, the Python source. `run(_context: str)` must be defined exactly once as the entry point.

Set `object.readOnly=true` only for inspection scripts that create, modify, or delete nothing. Read-only scripts may run while a command dialog is open, but modification attempts are rejected. Normal scripts require the open dialog to be closed. The script may use Fusion APIs such as `adsk.core` and `adsk.fusion`.

Printed text is returned as tool output. Exceptions must not be caught by `run`, because Fusion needs the exception message to report and diagnose failure.

#### Documents

- `operation="open"` requires `fileId`, obtained from a document search if needed.
- `operation="close"` may require `userConfirmedSaveAndClose=true` or `userConfirmedCloseWithoutSave=true` when unsaved changes exist.
- `operation="save"` saves the active document and should be used only when explicitly requested.

#### Purchase

A purchase operation requires:

- `purchaseInterest`: `fusion_subscription`, `extension`, or `flex`
- `userConfirmedOpenPurchaseManager=true`, only after the user explicitly agrees.
- Optional `extensionName` and `userMessageSummary`.

The tool must read licensing before purchase guidance or execution, unless licensing was already read with fresh results in the conversation. `fusion_subscription` is for plans/pricing or seats, `extension` is for Advanced capabilities/add-ons, and `flex` is for Flex tokens.

Education rules differ: Education users must not be offered commercial subscriptions or Flex token purchases; extensions should be described as free Edu Access and activated with `purchaseInterest="extension"`. Commercial and Personal users receive the relevant options returned by licensing. Active extensions must not be presented as purchases.

#### Image editing

`editImage` requires:

- `image_url`: signed URL of the source screenshot.
- `s3_url`: permanent source-image identifier.
- `prompt`: the exact natural-language edit or visualization request.

This operation is for previewing or rendering the model as an image. It does not alter the real Fusion design. It consumes one AI media generation use when an image is generated.

#### PowerPoint generation

`generatePowerpoint` requires a JSON string in `slides_json`. Each slide contains `slide_number` and a list of `placeholders` with:

- `idx`: placeholder index from the PowerPoint layout schema.
- `accepts`: `text`, `image`, or `any`.
- `value`: text or an `s3://` image URL.

The layout resource `resource://mcp.generate_powerpoint_schema` must be read first. Text placeholders require substantive content that fits the placeholder. Image placeholders must use `accepts="image"` or `accepts="any"`.

#### Image preview

`previewImage` requires matching `image_url` and `s3_url` values, and supports:

- `action="preview"`: preview a single image.
- `action="external"`: open a single image or presentation externally.
- `action="download"`: save a file or package multiple files as a ZIP.

`title` is optional. Arrays are supported only for matching multiple image URLs and require download action.

### `fusion_mcp_read`

**Required parameter:** `queryType`

Supported query types:

- `licensing` — returns license summary, services, active and purchasable extensions, and Flex token balances.
- `projects` — lists project names and IDs in the current hub.
- `document` — performs `search`, `open`, or `recent`:
  - `search` requires a name substring and optionally accepts a project name or ID.
  - `open` lists open documents and active/modified status.
  - `recent` lists recent documents.
- `apiDocumentation` — searches Fusion API documentation with `searchPattern`; optional `apiCategory` and `filter`.
- `screenshot` — captures the active graphics view as a PNG.
- `activeCommand` — reads the open command dialog, default-command state, and visible input values.

Additional `apiDocumentation` categories are `class`, `member`, `description`, and `all`. Filters use dot-separated namespaces or class names, such as `adsk.cam` or `adsk.fusion.Extrude`.

Screenshot options:

- `width` and `height`, 32–4096 pixels.
- `antiAliasing`, default true.
- `transparentBackground`, default true.
- `direction`: `current`, `front`, `back`, `bottom`, `top`, `left`, `right`, `iso-bottom-left`, `iso-bottom-right`, `iso-top-left`, or `iso-top-right`.

The screenshot result contains `type`, `mimeType`, and base64-encoded `base64Data`. Active-command input types include values, checkboxes, dropdowns, selections, strings, tables, buttons, and custom inputs.

### `fusion_mcp_update`

**Required parameter:** `featureType`, either:

- `undo` — undoes the most recent committed operation.
- `redo` — redoes the most recently undone operation.

Undo and redo cannot run during preview or interactive commands. Responses indicate whether undo and redo remain available.

## Exchange sequence

1. Send `initialize` with the protocol version and client information.
2. Inspect the server capabilities and server information returned by `initialize`.
3. Send `tools/list` with an empty parameter object.
4. Retrieve every tool's name, description, and input schema before invoking it.
5. Re-read schemas or discovery resources whenever tool behavior or available entities may have changed.
