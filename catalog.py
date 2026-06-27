"""
GRYPHX product catalog and sizing data — single source of truth.
Keeping this as plain data (not prose buried in a prompt) means the bot
can't "invent" details: it can only say what's actually in here.
"""

PRODUCTS = {
    "plain_tshirt": {
        "name": "Plain T-Shirt",
        "colors": ["Black", "White"],
        "sizes": ["L (42)", "XL (44)", "2XL (46)"],
        "category": "tshirt",
    },
    "graphic_tshirt": {
        "name": "GRYPHX Graphic T-Shirt",
        "colors": ["Black", "White"],
        "sizes": ["L (42)", "XL (44)", "2XL (46)"],
        "category": "tshirt",
    },
    "linen_pants": {
        "name": "Plain Linen Pants",
        "colors": ["Cream Off White"],
        "sizes": ["XL", "2XL", "3XL"],
        "category": "pants",
    },
}

# T-shirt sizing: chest size (inches) per label.
# IMPORTANT: GRYPHX t-shirts are CROP FIT, which runs closer to the body
# than a standard tee at the same label. Sizing logic (sizing.py) is
# anchored on a verified real fit: 5'9" / 69kg -> XL (44) fits perfectly.
TSHIRT_SIZE_CHART = {
    "L (42)": {"chest_in": 42, "length_in": 25},
    "XL (44)": {"chest_in": 44, "length_in": 26},
    "2XL (46)": {"chest_in": 46, "length_in": 27},
}

# Reference fitting point for linen pants, given in the spec:
# 5'9" / 69kg fits comfortably in 2XL. We derive a simple BMI-style scale
# around this anchor to place other height/weight combos onto XL/2XL/3XL.
LINEN_PANTS_REFERENCE = {
    "height_in": 69,  # 5'9" in inches
    "weight_kg": 69,
    "size": "2XL",
}

LINEN_PANTS_SIZES = ["XL", "2XL", "3XL"]

SMALLEST_TSHIRT = "L (42)"
LARGEST_TSHIRT = "2XL (46)"
SMALLEST_PANTS = "XL"
LARGEST_PANTS = "3XL"

SOCIAL = {
    "instagram": "@gryphx.clo",
    "whatsapp": "+9779814861511",
}