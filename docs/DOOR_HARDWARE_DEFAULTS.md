# Saved hardware functions on new plans

New-plan intake writes `door_hardware_specifications.json` using the job's frozen
`doors.interior_hardware_by_room` policy. It shares the optional `door_schedule`
input documented in [Door core defaults](DOOR_CORE_DEFAULTS.md).

Each opening can supply `door_type` (`hinged`, `pocket`, `bypass`, `bifold`,
`sliding` or `unknown`) and `door_type_source`. Both the room association and door
type need nonempty source references before a company default applies.

With the current saved company policy:

| Reviewed interior opening | Hardware function |
| --- | --- |
| Hinged bedroom, bathroom or toilet room | Privacy |
| Hinged other interior room or closet | Passage |
| Pocket door serving a toilet room | Privacy latch |
| Pocket door serving a closet | Passage pull |

Pocket closets require the explicit `closet` room class; `other_interior` alone
does not establish closet use. The separate core resolver retains its existing
room classes, so a `closet` record needs a sourced `project_core` selection to
resolve its core until that classification is supported there.

Garage entries, exterior doors, special assemblies, bypass doors, unidentified
rooms/types and unsourced associations do not inherit ordinary hardware. Open
passages remain doorless. A per-opening `project_hardware` needs a nonempty
`project_hardware_source`, takes precedence and records conflicts. A frozen
project override of the company hardware policy also takes precedence.

The reader checks the frozen plan, profile, resolved intake, source schedule and
derived file. Measurement checks before and after extraction and records the
hardware file hash and unresolved opening IDs in its summary. A missing file
declared by new intake is an error; an older job without the new artifact remains
unchanged and receives no silently injected policy.

These are hardware functions, not purchase counts or approved products. Complete
door enumeration, source accuracy, leaf counts, handing, compatible product sizes,
stops, installation ownership and pricing remain separate work. No complete
schedule, purchase release or whole-house completion is asserted.

Verification: 81 focused tests cover hardware/core rules, policy revisions,
new-plan intake/measurement and company defaults. An actual intake CLI trial in
`outputs/new_plan_hardware_defaults` assigns the four expected functions and
leaves garage/unknown openings unresolved. A second intake refuses to overwrite
the job. This is a synthetic workflow trial, not unseen-plan accuracy validation.

The editable opening schedule also resolves hardware through
`apply_hardware_policy`. It uses current `room_class`, `door_configuration` and
the source-bound role review. Optional `project_hardware` and
`project_hardware_source` pass through only while that opening review is current.
Pocket configurations use their explicit saved rule; other special assemblies
remain separate. Geometry edits that invalidate the role review also withhold
hardware, including project overrides.

The ordinary core and hardware policies are read independently. An older job can
apply a narrow hardware revision with `door_hardware_policy_revision.json`, using
the same source hashes and contained paths as `door_policy_revision.json`.
Updating a core policy does not update hardware. Project overrides survive either
revision; unrelated defaults remain frozen.

The opening bid scope includes the saved hardware function and provenance but
still requires compatible products, quantities and package inclusions. Its
fingerprint changes with the underlying schedule/policy. LEVEL GROUND reviewer
retrieval watches both policy revision files and referenced profiles for changes
during retrieval. The homeowner reference continues to exclude private policies.

Live verification: 74 related tests passed. An isolated copy of the existing Burns
review produced five privacy and seven passage assignments. Actual HTTP saved
wall edits withheld the affected hardware and bid reference, restoration recovered
them, and changing the policy profile was rejected. Original files were unchanged.
Seven hardware functions remain unresolved, including a pocket closet whose older
room classification is only `other_interior`; no location-name inference is made.
Evidence: `outputs/live_door_hardware/checks.json`. This development-exposed case
does not establish unseen-plan accuracy or automatic full-plan enumeration.

`opening_quantity_review.default_mapping` also identifies the Door knobs allowance
by exact scope and adds `hardware_target` for new jobs. `hardware_quantity_review`
provides four separate EA set references as assembly inputs. Current single-leaf
reviews and known hardware functions are required; known zeros and unresolved
groups remain distinct. The reference allowance stays input-only and unpriced.
An explicit existing kit/count purchase review may create one supplemental cost
owner for each input. The measurement server resolves opening quantities before
purchase mappings, preserving markups and withholding dependent counts after
edits. Older mappings without `hardware_target` retain their existing behavior.

Ninety-one focused tests and actual HTTP count/purchase-mapping trials passed.
The purchase trial uses synthetic ownership records only; actual supplier
inclusions and products remain unverified. See `outputs/live_hardware_quantities`
and `outputs/hardware_purchase_mapping_trial`. No current price or complete
takeoff is inferred from those trials.

When `room_use_review.json` exists, the editable schedule resolves additional
room associations through `door_room_associations.associate`. Both measured faces
must connect to current source-reviewed rooms. Identical room classes or one
non-circulation class can resolve a missing door-room assignment. Different
non-circulation classes stay unresolved. Existing assignments are checked, and
`other_interior` may be refined to a source-reviewed closet. The live core-policy
adapter maps that closet subtype to the existing hollow-other-interior rule;
the standalone intake core resolver retains its original schema.

Room review evidence is included in the derived schedule, and bid retrieval
watches `room_use_review.json` for concurrent changes. Door association reads
room geometry/use without ceiling or wall-surface selection dependencies.
Sourced project overrides retain precedence. Sixty-seven focused tests and an
actual Burns-copy HTTP trial passed, including removal of a per-door bedroom
class, pocket-closet resolution, geometry edits and room-review changes. Evidence:
`outputs/live_door_room_associations`. Room-use review itself is still required;
this does not establish automatic whole-plan interpretation.

Supported native PDF labels can now supply candidate room uses without a saved
room-use review. `room_use_candidates` preserves source bindings and explicitly
marks inference as requiring review. Existing current reviews take precedence;
stale reviews, unlabeled regions and conflicting room labels are not replaced by
a guess. Native labels cannot override a conflicting reviewed door class. Both
opening faces must still connect to distinct compatible current regions.

The editable opening schedule invokes this recognition for interior doors when
the plan is available, including jobs with no room-use review file. An isolated
Burns HTTP trial recognized ten of seventeen measured regions; all ten matched
the saved source review used only for comparison. Seven unlabeled regions stay
unknown. The closet pocket door supplied a passage-pull reference. Sixty-seven
focused tests and actual edit/restore checks passed. See
`outputs/live_native_room_labels`. This development-exposed plan retains reviewed
wall/opening geometry and does not prove unattended or unseen-plan accuracy.

The `jj.py hardware-purchases` command now generates the four purchase mappings
from a job-specific, source-backed supply review. It uses live counts and original
template markups; supplier-included and unresolved functions add no separate cost.
See [automatic hardware purchase setup](HARDWARE_PURCHASE_SETUP.md) for the source
format and limits. No Roberts products, prices or quantities become company defaults.
