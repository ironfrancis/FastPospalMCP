from fastpospal.raw.builders import new_supplier_payload


def test_new_supplier_payload_defaults():
    payload = new_supplier_payload(user_id=123, name="测试供货商")
    assert payload["id"] == 0
    assert payload["userId"] == 123
    assert payload["name"] == "测试供货商"
    assert payload["businessMode"] == "0"
    assert payload["supplierExt"]["settlementType"] == "2"
    assert payload["supplierStore"]["enable"] == 0
