import pycountry


COUNTRIES = tuple(sorted(
    ({"code": country.alpha_2, "name": country.name} for country in pycountry.countries),
    key=lambda item: item["name"],
))
COUNTRY_NAMES = {item["code"]: item["name"] for item in COUNTRIES}
COUNTRY_CODES_BY_NAME = {item["name"].casefold(): item["code"] for item in COUNTRIES}


def country_code(value: str) -> str | None:
    normalized = value.strip()
    if normalized.upper() in COUNTRY_NAMES:
        return normalized.upper()
    return COUNTRY_CODES_BY_NAME.get(normalized.casefold())
