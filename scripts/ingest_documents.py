import asyncio

from app.lib.rag.ingestion.core import ingest_documents_batch

SOURCES = [
    # ============================================
    # USA - TSA & FAA
    # ============================================
    {"type": "url", "url": "https://www.tsa.gov/travel/security-screening", "country_code": "US"},
    {
        "type": "url",
        "url": "https://www.tsa.gov/sites/default/files/tsa-travel-checklist.pdf",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.tsa.gov/travel/security-screening/whatcanibring/all",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.tsa.gov/travel/security-screening/whatcanibring/all-list",
        "country_code": "US",
    },
    {"type": "url", "url": "https://www.faa.gov/hazmat/what_is_hazmat", "country_code": "US"},
    # ============================================
    # USA - Airlines
    # ============================================
    # Delta
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/overview",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/overview",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/additional-baggage-information/baggage-faqs",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/additional-baggage-information/general-conditions-and-rules",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/delayed-lost-damaged-baggage",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/ammunition-explosives-firearms",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/battery-or-fuel-powered",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/food-alcohol-transportation",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/personal-care-medical-items",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/robotic-machine-other",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/sporting-leisure-goods",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/tobacco-ecig-marijuana",
        "airline_code": "DL",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/other-items",
        "airline_code": "DL",
        "country_code": "US",
    },
    # American Airlines
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/checked-baggage-policy.jsp",
    #     "airline_code": "AA",
    #     "country_code": "US",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/carry-on-baggage.jsp",
    #     "airline_code": "AA",
    #     "country_code": "US",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/delayed-or-damaged-baggage.jsp",
    #     "airline_code": "AA",
    #     "country_code": "US",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/restricted-items.jsp",
    #     "airline_code": "AA",
    #     "country_code": "US",
    # },
    # United Airlines
    {
        "type": "url",
        "url": "https://www.united.com/en/us/fly/baggage.html",
        "airline_code": "UA",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.united.com/en/us/fly/baggage/carry-on-bags.html",
        "airline_code": "UA",
        "country_code": "US",
    },
    {
        "type": "url",
        "url": "https://www.united.com/en/us/fly/help/lost-and-found.html",
        "airline_code": "UA",
        "country_code": "US",
    },
    # ============================================
    # CANADA - CATSA
    # ============================================
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/carry-or-checked",
        "country_code": "CA",
    },
    {"type": "url", "url": "https://www.catsa-acsta.gc.ca/en/locked-baggage", "country_code": "CA"},
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/liquids-non-solid-food-personal-items",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/travelling-solid-food-items",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/item/solid-foods",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/duty-free-purchases",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/medication-and-medical-items",
        "country_code": "CA",
    },
    # ============================================
    # CANADA - Airlines
    # ============================================
    # Air Canada
    {
        "type": "url",
        "url": "https://www.aircanada.com/in/en/aco/home/plan/baggage/restricted-and-prohibited-items.html#/",
        "airline_code": "AC",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/carry-on.html#/",
        "airline_code": "AC",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/checked.html#/",
        "airline_code": "AC",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/special-items.html#/",
        "airline_code": "AC",
        "country_code": "CA",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/delayed-damaged-baggage.html",
        "airline_code": "AC",
        "country_code": "CA",
    },
    # ============================================
    # SOUTH KOREA - Airport Authority
    # ============================================
    {"type": "url", "url": "https://www.airport.kr/ap_en/1433/subview.do", "country_code": "KR"},
    {"type": "url", "url": "https://www.airport.kr/ap_en/1434/subview.do", "country_code": "KR"},
    {
        "type": "url",
        "url": "http://german.visitkorea.or.kr/svc/contents/infoHtmlView.do?vcontsId=140628",
        "country_code": "KR",
    },
    # ============================================
    # SOUTH KOREA - Airlines
    # ============================================
    # Korean Air
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/free-baggage",
        "airline_code": "KE",
        "country_code": "KR",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/restricted-item",
        "airline_code": "KE",
        "country_code": "KR",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/carry-on-baggage",
        "airline_code": "KE",
        "country_code": "KR",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/delayed-baggage",
        "airline_code": "KE",
        "country_code": "KR",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/damaged-baggage",
        "airline_code": "KE",
        "country_code": "KR",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/lost-item",
        "airline_code": "KE",
        "country_code": "KR",
    },
    # ============================================
    # PDFs
    # ============================================
    {
        "type": "pdf",
        "path": "./data/documents/south_korea/seat-prices-table-by-route-en.pdf",
        "country_code": "KR",
    },
    {"type": "pdf", "path": "./data/documents/usa/tsa-travel-checklist.pdf", "country_code": "US"},
]


async def main():
    print(" Starting document ingestion...\n")
    print(f" Total sources to process: {len(SOURCES)}\n")
    await ingest_documents_batch(SOURCES)
    print("\n Ingestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
