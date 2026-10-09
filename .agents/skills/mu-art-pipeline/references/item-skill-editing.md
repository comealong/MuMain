# Item and Skill natural-language editing

This reference defines how the agent turns a user's natural-language request into a precise data edit. The Python editors that will execute these operations are planned as repository tools outside the skill directory; they are not implemented in this phase. Do not claim that a change was written until an editing backend has actually saved it.

## Scope

- Edit existing item definitions and existing skill records.
- Defer map editing for a later design discussion. Dev Editor runtime tuning and the read-only Effect Browser are not part of this workflow.
- Do not create or delete item or skill records unless a later editor explicitly supports that operation.
- Keep 3D model, texture, and BMD mesh work on the existing Mu art pipeline.

## Resolve each request

1. Identify the target item or skill from the repository data, not from memory. Accept an item group and number such as (0,1), an exact/localized name, or a skill record index/name.
2. Search and show the candidate record before editing. If a name matches more than one item or skill, or the requested locale is unclear, ask which target the user means. Do not guess.
3. Translate the request into explicit field changes: target ID, source locale/file, field path, current value, requested value, and any requested range of records. Preserve the user's stated bounds and qualifiers.
4. If a field name or desired value is ambiguous, ask a focused question. Do not silently reinterpret an unsupported field as a similarly named one.

## Item data

Item definitions are JSON records under <code>src/bin/Data/Items/Group*_*.json</code>; the schema and valid values are documented in [item-data.md](../../../../docs/item-data.md). Find an item by its <code>group:number</code> identity, and edit only that record. Names are localized in the <code>name</code> object. The separate <code>src/bin/Data/Items/Models/</code> files control model presentation and should only be changed when the user asks for a model/display property.

Validate field types, enum names, number ranges, required English name, and duplicate IDs before saving. Keep the existing file encoding, JSON structure, and unrelated records unchanged.

## Deleting or retiring an item

An item definition is not a server drop-table entry. This checkout contains the client's item catalog but not the server's drop configuration. Removing a record from the client catalog leaves its indexed slot empty; it does not stop a server from sending that group/number. The client currently initializes missing slots as zeroed attributes rather than treating every omitted item as a startup error, so the failure may appear later as a nameless, incorrectly displayed, or unusable drop.

When the user says “delete an item”, distinguish the intended result before editing:

- To stop new drops, remove or disable the item in the authoritative server drop tables and keep the client definition so existing items remain recognizable.
- To retire it everywhere, inspect server drops, shops, quests, events, recipes, and persisted inventories/storage, migrate or remove existing instances, and reserve the numeric ID. Do not reuse it.
- Do not delete only the client JSON as a way to disable drops. If server configuration is not available, explain that the request cannot be completed end to end.

The future editor should reject a destructive delete when it finds references in scanned files, and report that external server tables could not be checked when their data is not available.

## Skill data

Skill editor records are stored in locale-specific encrypted BMD files below <code>src/bin/Data/Local/&lt;Locale&gt;/</code> (for example, the English <code>skill_eng.bmd</code>). Resolve a skill's numeric record index from the selected locale's actual file. Skill fields follow <code>src/source/Data/GameData/SkillData/SkillFieldDefs.h</code>; human terms such as “range”, “cooldown”, and “AG cost” must map to the corresponding declared field only after checking the record and field metadata.

These files are binary, encrypted, and checksummed. Never edit them as text or patch bytes without a format-aware writer. Keep the requested locale and legacy/current record format intact. The future Python editor must validate the file and recompute its checksum when saving.

## Write behavior

Until the code-tree Python editor is implemented, resolve a request into the exact target, locale, fields, current values, and intended new values, but do not mutate files through ad hoc scripts. Clearly say that the edit backend is pending and that nothing was saved.

Once the Python editor is available, a clear request should be applied directly without an extra confirmation. Before changing each source file, create a timestamped backup. Write atomically, validate the result, and report the changed target, old and new values, file path, and backup path. If validation fails, leave the source file unchanged.

If the target, locale, or requested semantics are ambiguous, stop and ask before writing. A user asking to “preview” or “show the diff” is an explicit request not to save yet.

## Examples

- “把短剑 (0,1) 的攻击速度改成 25。” resolves to item group 0, number 1, field <code>attackSpeed</code>, value 25.
- “把 Poison 技能的冷却改成 800 毫秒。” resolves the localized skill record first, then maps “cooldown” to its declared delay field; if several Poison records exist, ask which one.
- “所有 Dark Wizard 可用技能的能量需求减半。” requires enumerating the exact matching records, calculating each new value without underflow, and reporting the selected record count. If the user did not define whether rounding down is acceptable, ask.
