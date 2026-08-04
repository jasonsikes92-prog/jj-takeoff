"""Disabled legacy Dugger estimate builder.

The original script hard-coded core square-foot quantities and bypassed the
measured-area certification gate. Keeping that implementation, even below an
early exception, would make it too easy to re-enable accidentally.
"""


def build() -> dict:
    raise RuntimeError(
        "Legacy Dugger builder permanently disabled: it hard-coded core square-foot "
        "inputs. Rerun the plan through jnj_takeoff.run_takeoff(area_specs=..., "
        "evidence_dir=...) so every heated and framed component is measured twice, "
        "reconciled, and certified before pricing."
    )


if __name__ == "__main__":
    build()
