from app.domain import validators
from app.services import print_service


def test_blank_form_refused():
    # Only a fully blank form is refused — anything filled prints.
    _, errors = print_service.validate_print_data({})
    assert errors.get("__form")


def test_single_field_prints():
    cleaned, errors = print_service.validate_print_data({
        "purity_huid": "", "product_name": "Ring",
        "gross_weight": "", "less_weight": "", "copies": 1,
    })
    assert errors == {}
    assert cleaned["show_gross"] is False
    assert cleaned["show_net"] is False
    assert cleaned["net_weight"] is None


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


def test_less_computes_net():
    cleaned, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "0.100", "copies": 1,
    })
    assert errors == {}
    assert str(cleaned["net_weight"]) == "2.046"


def test_less_over_gross_rejected():
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "3.000", "copies": 1,
    })
    assert "less_weight" in errors


def test_less_negative_rejected():
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "-1", "copies": 1,
    })
    assert "less_weight" in errors


def test_empty_less_defaults_to_zero_net_equals_gross():
    cleaned, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "", "copies": 1,
    })
    assert errors == {}
    assert str(cleaned["net_weight"]) == "2.146"


def test_copies_max_limit():
    # At a time max 99 copies — more is rejected everywhere (form, API, spool).
    _, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "", "copies": 100,
    })
    assert "copies" in errors
    cleaned, errors = print_service.validate_print_data({
        "purity_huid": "18kt HUID", "product_name": "Ring",
        "gross_weight": "2.146", "less_weight": "", "copies": 99,
    })
    assert errors == {}
