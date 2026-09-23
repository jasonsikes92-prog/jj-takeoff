# Door-core practices on new plans

Company profile version 8 contains 38 practices. `doors.interior_core_by_room` assigns solid cores to bedrooms, bathrooms and toilet rooms, and hollow cores to explicitly identified other interior rooms. Unknown room associations never fall through to hollow. Garage entries, exterior doors and special interior assemblies require their own specifications. Open passages receive no door-core assignment. A sourced project selection takes precedence and retains any difference from the default.

`new_plan_intake.create_job` now writes `door_core_specifications.json` beside the frozen `company_profile_snapshot.json` and `estimate_intake.json`. Without door/room associations, the file retains the practice and explicitly says extraction is still needed. It does not invent a door count. Existing jobs are not migrated or overwritten when the company profile changes.

The existing `--project-inputs` JSON accepts an optional `door_schedule`:

```json
{
  "door_schedule": {
    "plan_sha256": "SHA256 of this exact source PDF",
    "source": "Reviewed plan sheet and opening/room association source",
    "openings": [
      {
        "opening_id": "D01",
        "scope": "interior",
        "room_class": "bedroom",
        "room_source": "Source identifying the room this door serves"
      }
    ]
  }
}
```

Replace the explanatory hash/source values with actual evidence. Allowed scopes are `interior`, `special_interior`, `garage_entry`, `exterior`, `open_passage` and `unknown`. Recognized room classes are `bedroom`, `bathroom`, `toilet_room` and `other_interior`; other or missing classes remain unresolved. Do not classify a bedroom closet as a bedroom merely because its label contains that word. Optional `project_core` (`solid` or `hollow`) requires `project_core_source`. Core selection alone never approves a required separation assembly.

The source schedule is saved as `door_schedule.json` with its plan hash. `door_specifications.read_door_specifications(job)` reproduces the result from the frozen profile and project inputs, verifying the plan, profile, intake and derived results. The measurement pipeline runs that check before extraction and again before exporting results. Its summary links the specification file and hash and distinguishes missing schedules, unresolved openings and incomplete enumeration. An altered source requires regeneration; old jobs without this new file retain their existing measurement workflow.

The core resolver does not change dimensions, handing, hardware, installation ownership, leaf counts, purchase quantities or prices. Hardware functions now have a [separate saved-policy resolver](DOOR_HARDWARE_DEFAULTS.md). Upload alone does not yet extract and verify all door/room associations automatically. These remaining interpretation and assembly tasks must be completed before a door order or whole-house estimate can be released.

Validation: eight door-specification tests, nine existing company-profile tests, 26 new-plan tests and nine LEVEL GROUND workspace/report tests passed. A separate Roberts intake used the reviewed associations for all 16 schedule entries and matched all 13 ordinary interior core assignments (six solid, seven hollow). Its garage entry stays separate, open passages stay doorless and bypass leaf counts remain unknown. This is development-exposed workflow validation, not unseen-plan accuracy evidence. Workspace evidence: `outputs/reusable_door_core_rules`.
