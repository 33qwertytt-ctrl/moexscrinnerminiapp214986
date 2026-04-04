from infrastructure.moex.parsers import parse_bonds


def test_parse_bonds_derives_company_name() -> None:
    payload = {
        "securities": {
            "columns": [
                "SECID",
                "SHORTNAME",
                "SECNAME",
                "COUPONPERCENT",
                "COUPONVALUE",
                "COUPONPERIOD",
                "FACEVALUE",
                "OFFERDATE",
                "MATDATE",
                "LOTVALUE",
                "RATING",
            ],
            "data": [
                [
                    "RU000TEST",
                    "МОНОП 1P04",
                    "МОНОПОЛИЯ 001P-04",
                    "15.5",
                    "12.9",
                    "30",
                    "1000",
                    None,
                    "2027-03-01",
                    "1000",
                    "ruA",
                ]
            ],
        },
        "marketdata": {
            "columns": ["SECID", "LAST"],
            "data": [["RU000TEST", "98.2"]],
        },
    }

    [bond] = parse_bonds(payload)

    assert bond.shortname == "МОНОП 1P04"
    assert bond.company_name == "МОНОПОЛИЯ"
