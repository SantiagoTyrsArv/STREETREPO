from app.shared.domain import geo_parameters


def test_geographic_parameters_match_the_thesis() -> None:
    # Guía 2.3: cambiarlos requiere aprobación del responsable.
    assert geo_parameters.DEDUPLICATION_RADIUS_M == 25.0
    assert geo_parameters.ROAD_MATCHING_RADIUS_M == 30.0
    assert geo_parameters.PROXIMITY_FULL_SCORE_RADIUS_M == 100.0
    assert geo_parameters.PROXIMITY_MAX_RADIUS_M == 500.0
