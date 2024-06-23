import csv
import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def get_exhibitor_details(page, url):
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
        await page.wait_for_selector('h1.wrap-word', timeout=30000)
    except TimeoutError as e:
        logging.error(f"Timeout loading {url}: {e}")
        return {'url': url, 'error': 'Timeout'}

    exhibitor = {'url': url}
    selectors = {
        'name': 'h1.wrap-word',
        'why_visit': 'div#exhibitor_details_showobjective p',
        'description': 'div#exhibitor_details_description p',
        'branch': ':text-is("Branch")',
        'product_categories': ':text-is("Product Categories")',
        'gallery': 'div.enhanced-slider',
        'documents': 'div.document-section',
        'website': 'a[href^="https://www.aatcc.org"]',
        'email': 'a[href^="mailto:"]',
        'phone': 'div#exhibitor_details_phone p a',
        'address': ':text-is("ADDRESS")'
    }

    for field, selector in selectors.items():
        try:
            if field == 'gallery':
                elements = await page.query_selector_all(f'{selector} div.slick-track div.slick-slide div.product-carousel-image-container div.product-text a.product-link')
                exhibitor[field] = [{'title': await el.inner_text(), 'url': await el.get_attribute('href')} for el in elements]
            elif field == 'documents':
                elements = await page.query_selector_all(f'{selector} div.inline-block.document-detail-container a')
                exhibitor[field] = [{'title': await el.inner_text(), 'url': await el.get_attribute('href')} for el in elements]
            elif field in ['website', 'email']:
                el = await page.query_selector(selector)
                if el:
                    text = await el.inner_text()
                    url = await el.get_attribute('href')
                    exhibitor[field] = {'text': text, 'url': url}
                else:
                    exhibitor[field] = {'text': '', 'url': ''}
            elif field == 'phone':
                el = await page.query_selector(selector)
                exhibitor[field] = await el.inner_text() if el else ''
            elif field in ['why_visit', 'description']:
                el = await page.query_selector(selector)
                exhibitor[field] = await el.inner_text() if el else ''
            else:
                el = await page.query_selector(f'{selector} ~ *')
                exhibitor[field] = await el.inner_text() if el else ''
        except Exception as e:
            logging.error(f"Error getting {field} from {url}: {e}")
            exhibitor[field] = ''

    exhibitor['name'] = await page.inner_text('h1.wrap-word')

    # Extract stand number
    try:
        stand_element = await page.query_selector('div.form-group-view-mode.wrap-word p')
        exhibitor['stand'] = await stand_element.inner_text() if stand_element else ''
    except Exception as e:
        logging.error(f"Error getting stand number from {url}: {e}")
        exhibitor['stand'] = ''

    return exhibitor

async def main():
    urls = []
    with open('exhibitor_urls.txt', 'r') as file:
        urls = [line.strip() for line in file if line.strip()]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        exhibitors = []
        for url in urls:
            exhibitor = await get_exhibitor_details(page, url)
            exhibitors.append(exhibitor)

        await browser.close()

    if exhibitors:
        keys = exhibitors[0].keys()
        with open('exhibitors.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(exhibitors)
        logging.info("Saved exhibitors to exhibitors.csv")
    else:
        logging.warning("No exhibitors found")

asyncio.run(main())
