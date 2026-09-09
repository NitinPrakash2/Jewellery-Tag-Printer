from app.domain import validators
from app.services import print_service


def test_required_fields():
    cleaned, errors = print_service.validate_print_data({})
    assert "purity_huid" in errors
    assert "product_name" in errors
    assert "gross_weight" in errors
    assert "net_weight" in errors


def test_non_numeric_weight():
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "abc", "net_weight": "2.146", "copies": 1,
    })
    assert "gross_weight" in errors


def test_negative_weight():
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "-1", "net_weight": "2.146", "copies": 1,
    })
    assert "gross_weight" in errors


def test_net_over_gross():
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.000", "net_weight": "2.146", "copies": 1,
    })
    assert "net_weight" in errors


def test_copies_bounds():
    _, e1 = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "net_weight": "2.146", "copies": 0,
    })
    assert "copies" in e1
    _, e2 = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "net_weight": "2.146", "copies": 100,
    })
    assert "copies" in e2


def test_valid_payload():
    cleaned, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "net_weight": "2.146", "copies": 1,
    })
    assert errors == {}
    assert cleaned["purity_huid"] == "18kt HUID"
    assert int(cleaned["copies"]) == 1
