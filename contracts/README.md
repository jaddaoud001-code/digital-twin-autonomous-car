# Contracts

Language-neutral data contracts shared by the components of the monorepo
(Unity simulator, Python analysis, and later the backend and dashboard).

A contract describes the shape of data exchanged between components: field
names, order, types, units and plausible value ranges. Producers and
consumers are tested against it, so a change on one side cannot silently
break the other.

## Contents

| File | Description |
|------|-------------|
| [telemetry/telemetry-sample.v1.schema.json](telemetry/telemetry-sample.v1.schema.json) | One telemetry sample (one CSV row) written by the simulator at 10 Hz. JSON Schema draft 2020-12. |

For tabular formats (CSV), the order of the `required` array is the
authoritative column order.

## Versioning

- Each contract carries its major version in its file name: `*.v1.schema.json`,
  `*.v2.schema.json`, ...
- Backward-compatible changes (better descriptions, typo fixes, tightening
  documentation) may be made in place.
- Any incompatible change (adding, removing, renaming or reordering a field,
  changing a type, unit or bound in a way that rejects previously valid data)
  requires a **new file** with the next version number. The old version is
  kept as long as data or code still depends on it.
- Producers and consumers must be updated in the same change as the contract;
  the cross-language tests in `ml/maintenance/tests/` enforce this for
  telemetry.
