import json
import scrapy
import time


class AlcoholSpider(scrapy.Spider):
    name = 'alcohol'
    allowed_domains = ['amwine.ru']
    start_urls = ['https://amwine.ru/catalog/krepkie_napitki/']
    category_list = ['konyak', 'vodka']
    section_id_list = [18, 29]
    headers = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'user_agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.82 Mobile Safari/537.36'
    }


    def start_request(self):
        mainpage_url = "https://amwine.ru/catalog/krepkie_napitki/konyak/"
        scrapy.Request(mainpage_url,
                       callback=self.parse
                       )

    def parse(self, response):
        #page_count = response.css('ul.catalog-pagination li::text')[5].get().strip()
        #int(page_count)
        page_count = 10
        request_url = 'https://amwine.ru/local/components/adinadin/catalog.section.json/ajax_call.php'
        for i in range(2):
            for page in range(1, page_count):
                category = self.category_list[i]
                section_id = self.section_id_list[i]
                yield scrapy.Request(request_url,
                                     body=f'json=y&params%5BIBLOCK_TYPE%5D=catalog&params%5BIBLOCK_ID%5D=2&params%5BCACHE_TYPE%5D=Y&params%5BCACHE_TIME%5D=3600&params%5BSECTION_ID%5D={section_id}&params%5BSECTION_CODE%5D={category}&params%5BPRICE_CODE%5D=MOSCOW&params%5BPAGE_ELEMENT_COUNT%5D=18&params%5BFILTER_NAME%5D=arrFilterCatalog&params%5BSORT_ORDER%5D=ASC&params%5BSORT_FIELD%5D=SORT&params%5BMESSAGE_404%5D=&params%5BSET_STATUS_404%5D=&params%5BSHOW_404%5D=Y&params%5BFILE_404%5D=&params%5BNO_INDEX_NO_FOLLOW%5D=N&params%5BCURRENT_PAGE%5D=1&params%5B~IBLOCK_TYPE%5D=catalog&params%5B~IBLOCK_ID%5D=2&params%5B~CACHE_TYPE%5D=Y&params%5B~CACHE_TIME%5D=3600&params%5B~SECTION_ID%5D={section_id}&params%5B~SECTION_CODE%5D={category}&params%5B~PRICE_CODE%5D=MOSCOW&params%5B~PAGE_ELEMENT_COUNT%5D=18&params%5B~FILTER_NAME%5D=arrFilterCatalog&params%5B~SORT_ORDER%5D=ASC&params%5B~SORT_FIELD%5D=SORT&params%5B~MESSAGE_404%5D=&params%5B~SET_STATUS_404%5D=&params%5B~SHOW_404%5D=Y&params%5B~FILE_404%5D=&params%5B~NO_INDEX_NO_FOLLOW%5D=N&params%5B~CURRENT_PAGE%5D=1&current_filter%5BACTIVE%5D=Y&current_filter%5BIBLOCK_ID%5D=2&current_filter%5BINCLUDE_SUBSECTIONS%5D=Y&current_filter%5BSECTION_ID%5D=18&PAGEN_1={page}&sort=sort',
                                     headers={'content-type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                                     method='POST',
                                     callback=self.parse_request
                                     )

    def parse_request(self, response):
        """Парсит url-ссылку на товар."""
        data = json.loads(response.body)
        url = 'https://amwine.ru/catalog/'
        for item in data['products']:
            href = item['link']
            url = response.urljoin(href)
            yield scrapy.Request(url, callback=self.parse_alco)

    def parse_alco(self, response):
        """Парсит информацию о товаре."""
        # Брэнд
        brand_data = response.css('div.detail-product-description a::text').get()
        if brand_data is not None:
            brand = brand_data.strip()
        else:
            brand = 'Неизвестно'

        # Иерархия разделов
        sections = []
        for section in response.css('div.breadcrumbs a::text').getall():
            sections.append(section)

        current_price = response.css('.catalog-element-info__price_detail span:not([class])::text').get().replace(" ", "")
        current_price = current_price.replace(u'\xa0', u' ')
        current_price = float(current_price)
        original_price = (response.css('div.catalog-element__wrap span::text').get())
        if original_price is not None:
            original_price = original_price.replace(" ", "")
            original_price = original_price.replace(u'\xa0', u' ')
            original_price = float(original_price)
            proc = (current_price / original_price) * 100
        else:
            proc = 0
            original_price = current_price

        # Наличие товара в магазине
        stock_str = response.css('div.catalog-element-info__shops-right a::text').get().strip()
        if stock_str.find("Нет") == -1:
            stock = True
        else:
            stock = False

        # Ссылка на основную картинку
        url_image = 'https://amwine.ru/'
        href_image = response.css('div.catalog-element-info__picture img::attr(src)').get()
        url_image = response.urljoin(href_image)

        # Правый блок описания товара
        discription_right_title = []
        discription_right = ''
        i = 0
        for params in response.css('div.about-wine__block div.h4::text').getall():
            params.strip()
            if params.find(':') == -1:
                params += ":"
            discription_right_title.append(params)
        for params1 in response.css('div.about-wine__block p::text').getall():
            params1.strip()
            if params1.find('\n') == 0:
                i -= 1
                discription_right += " " + params1 + "; "
            else:
                discription_right += discription_right_title[i] + " " + params1 + "; "
            i += 1

        item = {
            'timestamp': time.time(),  # Текущее время в формате timestamp
            'RPC': response.css('div.catalog-element-info__article span::text').get().replace(" ", ""),
            # {str} Уникальный код товара
            'url': str(response.request.url),  # {str} Ссылка на страницу товара
            'title': response.css('div.catalog-element-info__title h1::text').get().strip(),
            # {str} Заголовок/название товара
            'brand': brand,  # {str} Брэнд товара
            'section': sections,  # {list of str} Иерархия разделов
            'price_data': {
                'current': current_price,  # {float} Цена со скидкой, если скидки нет то = original
                'original': original_price,  # {float} Оригинальная цена
                'sale_tag': f'Скидка {proc}%',  # {str} Скидка
            },
            'stock': stock,  # {bool} Должно отражать наличие товара в магазине
            'main_image': str(url_image),  # {str} Ссылка на основное изображение товара
            "description": discription_right
            # {str} Описание товар Ниже добавить все характеристики которые могут быть на
            # странице тоавара, такие как Артикул, Код товара, Цвет, Объем, Страна производитель и т.д.
        }
        yield item
