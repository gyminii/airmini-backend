import asyncio

from app.lib.rag.ingestion import ingest_documents_batch

SOURCES = [
    # ============================================
    # USA - TSA & FAA
    # ============================================
    {"type": "url", "url": "https://www.tsa.gov/travel/security-screening"},
    {
        "type": "url",
        "url": "https://www.tsa.gov/sites/default/files/tsa-travel-checklist.pdf",
    },
    {
        "type": "url",
        "url": "https://www.tsa.gov/travel/security-screening/whatcanibring/all",
    },
    {
        "type": "url",
        "url": "https://www.tsa.gov/travel/security-screening/whatcanibring/all-list",
    },
    {"type": "url", "url": "https://www.faa.gov/hazmat/what_is_hazmat"},
    # # ============================================
    # # USA - Airlines
    # # ============================================
    # # Delta
    {"type": "url", "url": "https://www.delta.com/kr/en/baggage/overview"},
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/overview",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/additional-baggage-information/baggage-faqs",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/additional-baggage-information/general-conditions-and-rules",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/delayed-lost-damaged-baggage",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/ammunition-explosives-firearms",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/battery-or-fuel-powered",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/food-alcohol-transportation",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/personal-care-medical-items",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/robotic-machine-other",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/sporting-leisure-goods",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/tobacco-ecig-marijuana",
    },
    {
        "type": "url",
        "url": "https://www.delta.com/kr/en/baggage/prohibited-or-restricted-items/other-items",
    },
    # # American Airlines
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/checked-baggage-policy.jsp",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/carry-on-baggage.jsp",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/delayed-or-damaged-baggage.jsp",
    # },
    # {
    #     "type": "url",
    #     "url": "https://www.aa.com/i18n/travel-info/baggage/restricted-items.jsp",
    # },
    # United Airlines
    {"type": "url", "url": "https://www.united.com/en/us/fly/baggage.html"},
    {
        "type": "url",
        "url": "https://www.united.com/en/us/fly/baggage/carry-on-bags.html",
    },
    {"type": "url", "url": "https://www.united.com/en/us/fly/help/lost-and-found.html"},
    # ============================================
    # CANADA - CATSA
    # ============================================
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/carry-or-checked",
    },
    {"type": "url", "url": "https://www.catsa-acsta.gc.ca/en/locked-baggage"},
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/liquids-non-solid-food-personal-items",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/travelling-solid-food-items",
    },
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/item/solid-foods",
    },
    {"type": "url", "url": "https://www.catsa-acsta.gc.ca/en/duty-free-purchases"},
    {
        "type": "url",
        "url": "https://www.catsa-acsta.gc.ca/en/what-can-bring/medication-and-medical-items",
    },
    # ============================================
    # CANADA - Airlines
    # ============================================
    # Air Canada
    {
        "type": "url",
        "url": "https://www.aircanada.com/in/en/aco/home/plan/baggage/restricted-and-prohibited-items.html#/",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/carry-on.html#/",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/checked.html#/",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/special-items.html#/",
    },
    {
        "type": "url",
        "url": "https://www.aircanada.com/ca/en/aco/home/plan/baggage/delayed-damaged-baggage.html",
    },
    # ============================================
    # SOUTH KOREA - Airport Authority
    # ============================================
    {"type": "url", "url": "https://www.airport.kr/ap_en/1433/subview.do"},
    {"type": "url", "url": "https://www.airport.kr/ap_en/1434/subview.do"},
    {
        "type": "url",
        "url": "http://german.visitkorea.or.kr/svc/contents/infoHtmlView.do?vcontsId=140628",
    },
    # ============================================
    # SOUTH KOREA - Airlines
    # ============================================
    # Korean Air
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/free-baggage",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/restricted-item",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/carry-on-baggage",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/delayed-baggage",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/damaged-baggage",
    },
    {
        "type": "url",
        "url": "https://www.koreanair.com/contents/plan-your-travel/baggage/delayed-damaged-lost/lost-item",
    },
]
PDFS = [
    {
        "type": "pdf",
        "path": "./data/documents/south_korea/seat-prices-table-by-route-en.pdf",
    },
    {"type": "pdf", "path": "./data/documents/usa/tsa-travel-checklist.pdf"},
]


async def main():
    print(" Starting document ingestion...\n")
    print(f" Total sources to process: {len(PDFS)}\n")
    await ingest_documents_batch(PDFS)
    print("\n Ingestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
