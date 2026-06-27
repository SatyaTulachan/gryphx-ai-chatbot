"""
Size recommendation logic.

T-shirts: estimate chest size from height + weight (a standard approximation
used by sizing calculators), then map to the closest available chest size.

Linen pants: scale outward from the single reference point given
(5'9" / 69kg -> 2XL) using a BMI-like ratio, then snap to the nearest
available size.
"""

from catalog import (
    TSHIRT_SIZE_CHART,
    LINEN_PANTS_REFERENCE,
    LINEN_PANTS_SIZES,
    SMALLEST_TSHIRT,
    LARGEST_TSHIRT,
    SMALLEST_PANTS,
    LARGEST_PANTS,
)


def estimate_chest_inches(height_cm: float, weight_kg: float) -> float:
    """
    Rough chest-circumference estimate from height + weight.

    GRYPHX t-shirts are CROP FIT, which runs smaller/closer to the body
    than a standard tee at the same labeled size — so the size mapping is
    anchored on a verified real fitting point, not a generic average:

      - 175cm (5'9") / 69kg -> XL (44) fits perfectly (confirmed fitting)

    BMI matters more than height alone for chest size, since chest
    circumference tracks mass/frame more than height by itself.
    """
    bmi = weight_kg / ((height_cm / 100) ** 2)

    ref_height_cm = 175.26  # 5'9"
    ref_bmi = 69 / ((ref_height_cm / 100) ** 2)  # ~22.46
    ref_chest = 44.0  # XL, confirmed real fit at the reference point

    height_delta_in = (height_cm - ref_height_cm) / 2.54
    bmi_delta = bmi - ref_bmi

    chest = ref_chest + (height_delta_in * 0.15) + (bmi_delta * 1.1)
    return chest


def recommend_tshirt_size(height_cm: float, weight_kg: float) -> tuple[str, bool, bool]:
    """
    Returns (size_label, was_clamped_small, was_clamped_large)
    """
    target_chest = estimate_chest_inches(height_cm, weight_kg)

    closest_size = None
    smallest_diff = float("inf")
    for label, info in TSHIRT_SIZE_CHART.items():
        diff = abs(info["chest_in"] - target_chest)
        if diff < smallest_diff:
            smallest_diff = diff
            closest_size = label

    smallest_chest = TSHIRT_SIZE_CHART[SMALLEST_TSHIRT]["chest_in"]
    largest_chest = TSHIRT_SIZE_CHART[LARGEST_TSHIRT]["chest_in"]

    # Only flag as "out of range" when the estimate falls meaningfully
    # below/above what we stock — not just on the small/large side of
    # a size that still fits them fine.
    clamped_small = target_chest < smallest_chest - 4
    clamped_large = target_chest > largest_chest + 4

    return closest_size, clamped_small, clamped_large


def recommend_pants_size(height_cm: float, weight_kg: float) -> tuple[str, bool, bool]:
    """
    Scales from the single reference point (5'9"/69kg -> 2XL) using a
    BMI-ratio heuristic, then snaps to nearest available pants size.
    """
    ref_height_cm = LINEN_PANTS_REFERENCE["height_in"] * 2.54
    ref_weight = LINEN_PANTS_REFERENCE["weight_kg"]
    ref_bmi = ref_weight / ((ref_height_cm / 100) ** 2)

    customer_bmi = weight_kg / ((height_cm / 100) ** 2)
    bmi_delta = customer_bmi - ref_bmi

    # Reference sits at index 1 (2XL) of ["XL", "2XL", "3XL"].
    # Roughly 4 BMI points per size step.
    ref_index = LINEN_PANTS_SIZES.index(LINEN_PANTS_REFERENCE["size"])
    step = bmi_delta / 4.0
    target_index = ref_index + step

    rounded_index = round(target_index)
    clamped_small = rounded_index < 0
    clamped_large = rounded_index > len(LINEN_PANTS_SIZES) - 1
    final_index = max(0, min(len(LINEN_PANTS_SIZES) - 1, rounded_index))

    return LINEN_PANTS_SIZES[final_index], clamped_small, clamped_large


def height_to_cm(feet: int, inches: int) -> float:
    total_inches = feet * 12 + inches
    return total_inches * 2.54