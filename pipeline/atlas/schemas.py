_metric_or_null = {"type": ["number", "null"]}

STATION_ENTRY = {
    "type": "object",
    "required": ["id", "name", "ward", "lines", "lon", "lat", "metrics", "label"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "minLength": 1},
        "name": {"type": "string"},
        "ward": {"type": "string"},
        "lines": {"type": "array", "items": {"type": "string"}},
        "lon": {"type": "number"}, "lat": {"type": "number"},
        "label": {"type": "string"},
        "metrics": {
            "type": "object",
            "required": ["median_ppsm", "tx_count", "growth_1y", "growth_3y",
                         "growth_5y", "volatility", "dispersion", "liquidity_score",
                         "relative_value", "hazard_score", "pop_resilience",
                         "gravity", "confidence"],
            "additionalProperties": False,
            "properties": {
                "median_ppsm": {"type": "number"},
                "tx_count": {"type": "integer"},
                "growth_1y": _metric_or_null, "growth_3y": _metric_or_null,
                "growth_5y": _metric_or_null, "volatility": _metric_or_null,
                "dispersion": _metric_or_null,
                "liquidity_score": {"type": "number"},
                "relative_value": _metric_or_null,
                "hazard_score": _metric_or_null,
                "pop_resilience": _metric_or_null,
                "gravity": {"type": "number"},
                "confidence": {"type": "integer", "minimum": 0, "maximum": 2},
            },
        },
    },
}

STATIONS_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "asof", "stations"],
    "properties": {
        "schema_version": {"type": "integer"},
        "asof": {"type": "string", "pattern": "^\\d{4}Q[1-4]$"},
        "stations": {"type": "array", "minItems": 1, "items": STATION_ENTRY},
    },
}

QUARTERS_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "quarters", "stations"],
    "properties": {
        "schema_version": {"type": "integer"},
        "quarters": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "stations": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["m", "n"],
                "properties": {
                    "m": {"type": "array", "items": {"type": ["number", "null"]}},
                    "n": {"type": "array", "items": {"type": "integer"}},
                },
            },
        },
    },
}

DETAIL_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "id", "name", "series", "similar", "hazard", "landprice"],
    "properties": {
        "schema_version": {"type": "integer"},
        "id": {"type": "string"}, "name": {"type": "string"},
        "series": {
            "type": "object",
            "required": ["quarters", "median_ppsm", "tx_count"],
            "properties": {
                "quarters": {"type": "array", "items": {"type": "string"}},
                "median_ppsm": {"type": "array", "items": {"type": ["number", "null"]}},
                "tx_count": {"type": "array", "items": {"type": "integer"}},
            },
        },
        "similar": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "median_ppsm", "price_gap"],
                "properties": {
                    "id": {"type": "string"}, "name": {"type": "string"},
                    "median_ppsm": {"type": ["number", "null"]},
                    "price_gap": {"type": ["number", "null"]},
                },
            },
        },
        "hazard": {"type": ["object", "null"]},
        "landprice": {"type": ["object", "null"]},
    },
}

META_SCHEMA = {
    "type": "object",
    "required": ["schema_version", "asof", "generated_rows", "sources"],
    "properties": {
        "schema_version": {"type": "integer"},
        "asof": {"type": "string", "pattern": "^\\d{4}Q[1-4]$"},
        "generated_rows": {"type": "object"},
        "sources": {"type": "object"},
    },
}
