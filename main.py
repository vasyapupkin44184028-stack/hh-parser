import requests
import pandas as pd
import time
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from urllib.parse import urlparse, quote_plus
from datetime import datetime
from fake_useragent import UserAgent
from playwright.sync_api import sync_playwright
import random

class HHApiClient:
    def __init__(self):
        self.base_url = "https://api.hh.ru"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
        })
        self.regions_cache = None
    
    def load_regions(self):
        if self.regions_cache is not None:
            return self.regions_cache
            
        try:
            print("🔄 Загружаем список регионов...")
            response = self.session.get(f"{self.base_url}/areas", timeout=10)
            if response.status_code == 200:
                regions_data = response.json()
                regions_dict = {}
                
                def parse_areas(areas):
                    for area in areas:
                        area_name = area['name'].lower()
                        regions_dict[area_name] = area['id']
                        if area['id'] == '1':
                            regions_dict['мск'] = '1'
                            regions_dict['moscow'] = '1'
                        elif area['id'] == '2':
                            regions_dict['спб'] = '2'
                            regions_dict['питер'] = '2'
                        elif area['id'] == '3':
                            regions_dict['екб'] = '3'
                        elif area['id'] == '4':
                            regions_dict['нск'] = '4'
                        elif area['id'] == '66':
                            regions_dict['нн'] = '66'
                        
                        if 'areas' in area and area['areas']:
                            parse_areas(area['areas'])
                
                parse_areas(regions_data)
                self.regions_cache = regions_dict
                print(f"✅ Загружено регионов: {len(regions_dict)}")
                return regions_dict
            else:
                print("❌ Ошибка загрузки регионов")
                return {}
        except Exception as e:
            print(f"❌ Ошибка при загрузке регионов: {e}")
            return {}
    
    def search_vacancies(self, text, area=113, page=0, per_page=100):
        url = f"{self.base_url}/vacancies"
        params = {
            'text': text,
            'area': area,
            'page': page,
            'per_page': per_page,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            print(f"❌ Ошибка API: {e}")
            return None

class CompanyWebsiteFinder:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.update_headers()
        self.website_cache = {}
        
        self.known_websites = {
            'совкомбанк': 'sovcombank.ru', 'neoflex': 'neoflex.ru', 'aston': 'aston.ru',
            'т-банк': 'tbank.ru', 'ibs': 'ibs.ru', 'алабуга': 'alabuga.ru', 'тинькофф': 'tinkoff.ru',
            'сбер': 'sber.ru', 'яндекс': 'yandex.ru', 'mail.ru': 'mail.ru', 'vkontakte': 'vk.com',
            'ozon': 'ozon.ru', 'wildberries': 'wildberries.ru', 'avito': 'avito.ru', 'dns': 'dns-shop.ru',
            'mvideo': 'mvideo.ru', 'ситилинк': 'citilink.ru', 'газпром': 'gazprom.ru', 'лукойл': 'lukoil.ru',
            'ржд': 'rzd.ru', 'ростех': 'rostec.ru', 'росатом': 'rosatom.ru', 'мегафон': 'megafon.ru',
            'мтс': 'mts.ru', 'билайн': 'beeline.ru', 'tele2': 'tele2.ru', 'топ': 'top-academy.ru',
            'idf': 'idfeurasia.com', 'eurasia': 'idfeurasia.com',
            'альфа': 'alfabank.ru', 'втб': 'vtb.ru', 'открытие': 'open.ru', 'росбанк': 'rosbank.ru',
            'qiwi': 'qiwi.com', 'лаборатория': 'kaspersky.ru', 'касперский': 'kaspersky.ru',
            '1с': '1c.ru', 'битрикс': 'bitrix24.ru', 'агвир': 'agvir.ru', 'медиалогия': 'mlg.ru',
            'контур': 'kontur.ru', 'скайенг': 'skyeng.ru', 'нетология': 'netology.ru',
            'гедеон': 'gideon.ru', 'сибинтек': 'sibintek.ru', 'фактор': 'factor.ru',
            'тема': 'tema.ru', 'телеком': 'tema.ru'
        }
    
    def update_headers(self):
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
    def find_company_website(self, company_name):
        if not company_name or company_name == "Не указано":
            return None
        
        if company_name in self.website_cache:
            return self.website_cache[company_name]
        
        start_time = time.time()
        print(f"🔍 Поиск сайта для: {company_name}")
        
        known_site = self.check_known_websites(company_name)
        if known_site:
            print(f"✅ Найден через известные сайты: {known_site}")
            self.website_cache[company_name] = known_site
            return known_site
        
        generated_site = self.fast_generate_website_url(company_name)
        if generated_site:
            print(f"✅ Найден через генерацию: {generated_site}")
            self.website_cache[company_name] = generated_site
            return generated_site
        
        playwright_site = self.playwright_search_ultra_fast(company_name)
        if playwright_site:
            print(f"✅ Найден через Playwright: {playwright_site}")
            self.website_cache[company_name] = playwright_site
            return playwright_site
        
        print(f"❌ Сайт не найден для: {company_name} (поиск занял {time.time()-start_time:.2f}с)")
        self.website_cache[company_name] = None
        return None
    
    def check_known_websites(self, company_name):
        clean_name = company_name.lower().strip()
        for known_company, domain in self.known_websites.items():
            if known_company in clean_name:
                url = f"https://{domain}"
                if self.ultra_fast_site_check(url):
                    return url
        return None
    
    def fast_generate_website_url(self, company_name):
        if not company_name:
            return None
        
        clean_name = re.sub(r'[\(\)\[\]\{\}]', '', company_name)
        clean_name = re.sub(r'[^\w\s]', ' ', clean_name).strip()
        if len(clean_name) < 2:
            return None
        
        name_variants = set()
        
        words = clean_name.split()
        if len(words) > 3:
            main_name = ' '.join(words[:2])
            name_variants.add(main_name.lower().replace(' ', ''))
            name_variants.add(main_name.lower().replace(' ', '-'))
        
        name_variants.add(clean_name.lower().replace(' ', ''))
        name_variants.add(clean_name.lower().replace(' ', '-'))
        
        translit_name = self.transliterate_cyrillic(clean_name)
        if translit_name:
            name_variants.add(translit_name.replace(' ', ''))
            name_variants.add(translit_name.replace(' ', '-'))
        
        domains = ['.ru', '.com', '.org', '.net']
        
        checked = 0
        for name in list(name_variants):
            for domain in domains:
                if checked >= 6:
                    break
                    
                url = f"https://{name}{domain}"
                if self.ultra_fast_site_check(url) and self.is_valid_company_site(url):
                    return url
                
                url_www = f"https://www.{name}{domain}"
                if self.ultra_fast_site_check(url_www) and self.is_valid_company_site(url_www):
                    return url_www
                
                checked += 1
        
        return None
    
    def transliterate_cyrillic(self, text):
        brand_exceptions = {
            'авито': 'avito', 'яндекс': 'yandex', 'сбер': 'sber', 'тинькофф': 'tinkoff',
            'мегафон': 'megafon', 'мтс': 'mts', 'билайн': 'beeline', 'теле2': 'tele2',
            'озон': 'ozon', 'вк': 'vk', 'маил': 'mail', 'топ': 'top', 'академия': 'academy',
            'eurasia': 'eurasia', 'idf': 'idf', 'альфа': 'alfa', 'втб': 'vtb',
            'qiwi': 'qiwi', 'лаборатория': 'kaspersky', 'касперский': 'kaspersky',
            'битрикс': 'bitrix', 'агвир': 'agvir', 'медиалогия': 'mlg',
            'контур': 'kontur', 'скайенг': 'skyeng', 'нетология': 'netology',
            'гедеон': 'gideon', 'сибинтек': 'sibintek', 'фактор': 'factor',
            'тема': 'tema', 'телеком': 'telecom', 'сдэк': 'cdek', 'почта': 'pochta',
            'алгоритмика': 'algorithmika', 'монолит': 'monolit'
        }
        
        text_lower = text.lower()
        for cyrillic, latin in brand_exceptions.items():
            if cyrillic in text_lower:
                return latin
        
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        result = []
        for char in text.lower():
            if char in translit_dict:
                result.append(translit_dict[char])
            elif char in 'abcdefghijklmnopqrstuvwxyz0123456789 -_':
                result.append(char)
            elif char == ' ':
                result.append(' ')
        
        return ''.join(result)
    
    def ultra_fast_site_check(self, url):
        try:
            response = requests.head(url, timeout=0.5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False
    
    def playwright_search_ultra_fast(self, company_name):
        start_time = time.time()
        
        strategies = [
            self._playwright_strategy_stealth,
            self._playwright_strategy_humanized,
            self._playwright_strategy_fast_headless
        ]
        
        for strategy in strategies:
            if time.time() - start_time > 2:
                break
                
            try:
                result = strategy(company_name)
                if result:
                    return result
            except:
                continue
        
        return None
    
    def _playwright_strategy_stealth(self, company_name):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # ИЗМЕНЕНО: было False, стало True
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-ipc-flooding-protection',
                    '--disable-hang-monitor',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-back-forward-cache',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-translate',
                    '--disable-web-security',
                    '--allow-running-insecure-content',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-client-side-phishing-detection',
                    '--disable-cookie-encryption',
                    '--disable-domain-reliability',
                    '--disable-print-preview',
                    '--disable-speech-api',
                    '--disable-sync',
                    '--disable-webaudio',
                    '--disable-webgl',
                    '--disable-webrtc',
                    '--force-color-profile=srgb',
                    '--metrics-recording-only',
                    '--mute-audio',
                    '--use-mock-keychain',
                    '--hide-scrollbars',
                    '--ignore-certificate-errors',
                    '--ignore-ssl-errors',
                    '--ignore-certificate-errors-spki-list',
                    '--log-level=3',
                    '--silent'
                ]
            )
            
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
            
            viewports = [
                {'width': 1920, 'height': 1080},
                {'width': 1366, 'height': 768},
                {'width': 1536, 'height': 864},
                {'width': 1280, 'height': 720}
            ]
            
            config = {
                'user_agent': random.choice(user_agents),
                'viewport': random.choice(viewports),
                'locale': 'ru-RU',
                'timezone_id': 'Europe/Moscow',
                'geolocation': {'latitude': 55.7558, 'longitude': 37.6173},
                'permissions': ['geolocation']
            }
            
            context = browser.new_context(
                viewport=config['viewport'],
                user_agent=config['user_agent'],
                locale=config['locale'],
                timezone_id=config['timezone_id'],
                geolocation=config['geolocation'],
                permissions=config['permissions']
            )
            
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(screen, 'width', {get: () => 1920});
                Object.defineProperty(screen, 'height', {get: () => 1080});
                Object.defineProperty(screen, 'colorDepth', {get: () => 24});
                Object.defineProperty(Notification, 'permission', {get: () => 'default'});
                window.chrome = {runtime: {}};
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)
            
            page = context.new_page()
            
            page.set_extra_http_headers({
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            try:
                clean_company = re.sub(r'[\(\)\[\]\{\}]', '', company_name)
                clean_company = re.sub(r'ИП\s+\w+\s+\w+', '', clean_company).strip()
                
                search_query = f"{clean_company} официальный сайт"
                search_url = f"https://yandex.ru/search/?text={quote_plus(search_query)}&lr=213"
                
                page.goto(search_url, wait_until='domcontentloaded', timeout=2000)
                
                page.wait_for_timeout(100)
                
                if page.query_selector('form[action*="checkcaptcha"], .captcha, .CheckboxCaptcha'):
                    browser.close()
                    return None
                
                found_urls = []
                
                organic_selectors = [
                    'a.organic__greenurl',
                    '.serp-item a[href*="http"]',
                    '.organic a[href*="http"]',
                    '[data-cid] a[href*="http"]',
                    '.Path-Item a[href*="http"]',
                    '.organic__path a',
                    '[data-log-node*="organic"] a',
                    '.Organic a[href*="http"]'
                ]
                
                for selector in organic_selectors:
                    links = page.query_selector_all(selector)
                    for link in links[:5]:
                        try:
                            href = link.get_attribute('href')
                            text = link.text_content().strip() if link.text_content() else ""
                            
                            if href:
                                real_url = self.extract_real_url(href)
                                if real_url and self.is_valid_company_site_strict(real_url, company_name):
                                    if self.is_relevant_link(text, company_name):
                                        found_urls.append(real_url)
                        except:
                            continue
                
                if not found_urls:
                    all_links = page.query_selector_all('a[href*="http"]')
                    for link in all_links[:10]:
                        try:
                            href = link.get_attribute('href')
                            text = link.text_content().strip() if link.text_content() else ""
                            
                            if (href and 
                                not href.startswith('https://yandex.ru') and
                                not href.startswith('https://google.ru')):
                                
                                company_words = company_name.lower().split()
                                text_lower = text.lower()
                                
                                relevant = any(word in text_lower for word in company_words if len(word) > 2)
                                
                                if relevant:
                                    real_url = self.extract_real_url(href)
                                    if real_url and self.is_valid_company_site_strict(real_url, company_name):
                                        found_urls.append(real_url)
                        except:
                            continue
                
                unique_urls = list(set(found_urls))
                
                if unique_urls:
                    best_url = self.choose_best_url(unique_urls, company_name)
                    browser.close()
                    return best_url
                
                browser.close()
                return None
                
            except Exception as e:
                browser.close()
                return None
    
    def _playwright_strategy_humanized(self, company_name):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # ИЗМЕНЕНО: было False, стало True
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-background-timer-throttling'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1366, 'height': 768},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ru-RU'
            )
            
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = context.new_page()
            
            try:
                clean_company = re.sub(r'[\(\)\[\]\{\}]', '', company_name)
                clean_company = re.sub(r'ИП\s+\w+\s+\w+', '', clean_company).strip()
                
                search_query = f"{clean_company} официальный сайт"
                search_url = f"https://yandex.ru/search/?text={quote_plus(search_query)}"
                
                page.goto(search_url, wait_until='domcontentloaded', timeout=2000)
                
                if page.query_selector('form[action*="checkcaptcha"]'):
                    browser.close()
                    return None
                
                found_urls = []
                
                organic_selectors = [
                    'a.organic__greenurl',
                    '.serp-item a[href*="http"]',
                    '.organic a[href*="http"]'
                ]
                
                for selector in organic_selectors:
                    links = page.query_selector_all(selector)
                    for link in links[:3]:
                        try:
                            href = link.get_attribute('href')
                            if href:
                                real_url = self.extract_real_url(href)
                                if real_url and self.is_valid_company_site_strict(real_url, company_name):
                                    found_urls.append(real_url)
                        except:
                            continue
                
                unique_urls = list(set(found_urls))
                
                if unique_urls:
                    best_url = self.choose_best_url(unique_urls, company_name)
                    browser.close()
                    return best_url
                
                browser.close()
                return None
                
            except Exception:
                browser.close()
                return None
    
    def _playwright_strategy_fast_headless(self, company_name):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,  # ИЗМЕНЕНО: было True, осталось True
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            try:
                clean_company = re.sub(r'[\(\)\[\]\{\}]', '', company_name)
                clean_company = re.sub(r'ИП\s+\w+\s+\w+', '', clean_company).strip()
                
                search_query = f"{clean_company} официальный сайт"
                search_url = f"https://yandex.ru/search/?text={quote_plus(search_query)}"
                
                page.goto(search_url, wait_until='domcontentloaded', timeout=20000)
                
                found_urls = []
                
                links = page.query_selector_all('a[href*="http"]')
                for link in links[:8]:
                    try:
                        href = link.get_attribute('href')
                        if href and not href.startswith('https://yandex.ru'):
                            real_url = self.extract_real_url(href)
                            if real_url and self.is_valid_company_site_strict(real_url, company_name):
                                found_urls.append(real_url)
                    except:
                        continue
                
                unique_urls = list(set(found_urls))
                
                if unique_urls:
                    best_url = self.choose_best_url(unique_urls, company_name)
                    browser.close()
                    return best_url
                
                browser.close()
                return None
                
            except Exception:
                browser.close()
                return None
    
    def extract_real_url(self, url):
        if 'yandex.ru/redir/' in url or 'clck' in url:
            try:
                return url
            except Exception:
                pass
        
        return url
    
    def is_relevant_link(self, link_text, company_name):
        if not link_text:
            return False
        
        company_words = company_name.lower().split()
        clean_company = re.sub(r'[\(\)\[\]\{\}]', '', company_name).lower()
        
        ignore_words = [
            'яндекс', 'yandex', 'google', 'карты', 'images', 'видео', 'новости',
            'маркет', 'перевести', 'найти', 'search', 'ещё', 'more', 'еще',
            'знакомства', 'расписания', 'погода', 'афиша', 'работа', 'вакансии',
            'резюме', 'hh.ru', 'headhunter', 'отзывы', 'рейтинг', 'купить', 'цена'
        ]
        
        if any(word in link_text.lower() for word in ignore_words):
            return False
        
        for word in company_words:
            if len(word) > 2 and word in link_text.lower():
                return True
        
        return False
    
    def choose_best_url(self, urls, company_name):
        if not urls:
            return None
        
        company_keywords = company_name.lower().split()
        best_score = 0
        best_url = urls[0]
        
        for url in urls:
            score = 0
            domain = urlparse(url).netloc.lower()
            
            for keyword in company_keywords:
                if len(keyword) > 2 and keyword in domain:
                    score += 3
            
            if domain.endswith('.ru'):
                score += 1
            if 'www.' in domain:
                score += 1
            
            if score > best_score:
                best_score = score
                best_url = url
        
        return best_url
    
    def is_valid_company_site(self, url):
        try:
            domain = urlparse(url).netloc.lower()
            
            blacklist = [
                'yandex.ru', 'yandex.com', 'ya.ru', 'google.com', 'google.ru',
                'vk.com', 'facebook.com', 'instagram.com', 'hh.ru', 'rabota.ru', 
                'superjob.ru', 'mail.ru', 'rambler.ru', '2gis.ru', 'gosuslugi.ru'
            ]
            
            if domain in blacklist:
                return False
                
            if any(bad in domain for bad in ['yandex.', 'google.']):
                return False
            
            return True
            
        except:
            return False
    
    def is_valid_company_site_strict(self, url, company_name=None):
        try:
            domain = urlparse(url).netloc.lower()
            
            blacklist = [
                'yandex.ru', 'yandex.com', 'ya.ru', 'google.com', 'google.ru',
                'vk.com', 'facebook.com', 'instagram.com', 'hh.ru', 'rabota.ru', 
                'superjob.ru', 'mail.ru', 'rambler.ru', '2gis.ru', 'gosuslugi.ru',
                'yandex.net', 'yastatic.net', 'yandex.st', 'yandex.ua', 'yandex.kz',
                'yandex.by', 'yandex.az', 'yandex.com.tr', 'kinopoisk.ru', 'market.yandex.ru',
                'youtube.com', 'twitter.com', 'linkedin.com', 't.me', 'telegram.me',
                'whatsapp.com', 'viber.com', 'skype.com', 'zoom.us', 'avito.ru',
                'cian.ru', 'irr.ru', 'banki.ru', 'sravni.ru'
            ]
            
            if domain in blacklist:
                return False
                
            if any(bad in domain for bad in [
                'yandex.', 'google.', 'mail.', 'rambler.', 'search.', 'images.',
                'video.', 'maps.', 'news.', 'market.', 'kinopoisk.', 'social.',
                'chat.', 'messenger.', 'app.', 'api.', 'cdn.', 'static.', 'ad.',
                'ads.', 'analytic', 'tracking'
            ]):
                return False
            
            main_domain = domain.split('.')[0]
            if len(main_domain) < 3:
                return False
            
            if company_name:
                company_lower = company_name.lower()
                company_words = [word for word in company_lower.split() if len(word) > 2]
                domain_matches = any(word in domain for word in company_words)
                
                if domain_matches:
                    return True
            
            return True
            
        except:
            return False

class HHParser:
    def __init__(self):
        self.ua = UserAgent()
        self.session = requests.Session()
        self.api_client = HHApiClient()
        self.website_finder = CompanyWebsiteFinder()
        self.results = []
    
    def search_vacancies_hybrid(self, keywords, area=113, total_vacancies=None, per_keyword=None):
        all_vacancies = []
        
        if per_keyword and per_keyword > 0:
            for keyword in keywords:
                print(f"🔍 Поиск вакансий по ключевому слову: '{keyword}' (лимит: {per_keyword})")
                api_vacancies = self.search_via_api(keyword, area, per_keyword)
                if api_vacancies:
                    all_vacancies.extend(api_vacancies)
                    print(f"✅ Найдено вакансий для '{keyword}': {len(api_vacancies)}")
        elif total_vacancies and total_vacancies > 0:
            vacancies_per_keyword = max(1, total_vacancies // len(keywords))
            print(f"🔍 Общий лимит: {total_vacancies} вакансий (~{vacancies_per_keyword} на ключевое слово)")
            
            for keyword in keywords:
                print(f"🔍 Поиск вакансий по ключевому слову: '{keyword}'")
                api_vacancies = self.search_via_api(keyword, area, vacancies_per_keyword)
                if api_vacancies:
                    all_vacancies.extend(api_vacancies)
                    print(f"✅ Найдено вакансий для '{keyword}': {len(api_vacancies)}")
        else:
            for keyword in keywords:
                print(f"🔍 Поиск вакансий по ключевому слову: '{keyword}' (без лимита)")
                api_vacancies = self.search_via_api(keyword, area, 100)
                if api_vacancies:
                    all_vacancies.extend(api_vacancies)
                    print(f"✅ Найдено вакансий для '{keyword}': {len(api_vacancies)}")
        
        unique_vacancies = []
        seen_urls = set()
        for vacancy in all_vacancies:
            url = vacancy.get('Ссылка_на_вакансию', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_vacancies.append(vacancy)
        
        print(f"📊 Итого уникальных вакансий: {len(unique_vacancies)}")
        return unique_vacancies
    
    def search_via_api(self, keyword, area=113, per_page=100):
        vacancies_data = []
        page = 0
        
        try:
            while len(vacancies_data) < per_page:
                data = self.api_client.search_vacancies(text=keyword, area=area, page=page, per_page=min(100, per_page - len(vacancies_data)))
                if not data or 'items' not in data or not data['items']:
                    break
                
                items = data['items']
                for vacancy in items:
                    if len(vacancies_data) >= per_page:
                        break
                    vacancy_info = self.process_api_vacancy(vacancy, keyword)
                    if vacancy_info:
                        vacancies_data.append(vacancy_info)
                
                page += 1
                if page >= data.get('pages', 1):
                    break
            
        except Exception as e:
            print(f"❌ Ошибка поиска вакансий: {e}")
        
        return vacancies_data
    
    def process_api_vacancy(self, vacancy, keyword):
        try:
            title = vacancy.get('name', 'Не указано')
            company_info = vacancy.get('employer', {})
            company_name = company_info.get('name', 'Не указано')
            vacancy_url = vacancy.get('alternate_url', '')
            
            company_website = self.website_finder.find_company_website(company_name)
            
            vacancy_data = {
                'Название_вакансии': title,
                'Ключевое_слово': keyword,
                'Компания': company_name,
                'Ссылка_на_вакансию': vacancy_url,
                'Сайт_компании': company_website if company_website else 'Не найден',
                'Город': self.extract_area(vacancy),
            }
            
            return vacancy_data
            
        except Exception as e:
            print(f"❌ Ошибка обработки вакансии: {e}")
            return None
    
    def extract_area(self, vacancy):
        area_info = vacancy.get('area', {})
        return area_info.get('name', 'Не указан')
    
    def generate_filename(self, keywords):
        main_keyword = keywords[0] if keywords else "vacancies"
        clean_keyword = re.sub(r'[<>:"/\\|?*]', '', main_keyword).replace(' ', '_')[:50]
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"{clean_keyword}_{current_time}.xlsx"
    
    def save_to_excel(self, keywords, custom_filename=None):
        if not self.results:
            print("❌ Нет данных для сохранения")
            return False, None
        
        try:
            df = pd.DataFrame(self.results)
            
            if not os.path.exists('results'):
                os.makedirs('results')
            
            filename = custom_filename if custom_filename else self.generate_filename(keywords)
            filepath = os.path.join('results', filename)
            
            column_mapping = {
                'Название_вакансии': 'Название вакансии',
                'Ключевое_слово': 'Ключевое слово', 
                'Компания': 'Компания',
                'Ссылка_на_вакансию': 'Ссылка на вакансию',
                'Сайт_компании': 'Сайт компании',
                'Город': 'Город'
            }
            
            df = df.rename(columns=column_mapping)
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Вакансии')
                
                workbook = writer.book
                worksheet = writer.sheets['Вакансии']
                
                from openpyxl.styles import Font
                link_font = Font(color="0563C1", underline="single")
                
                for row in range(2, len(df) + 2):
                    cell = worksheet[f'D{row}']
                    if cell.value and str(cell.value).startswith('http'):
                        cell.hyperlink = cell.value
                        cell.font = link_font
                    
                    cell = worksheet[f'E{row}']
                    if cell.value and str(cell.value).startswith('http'):
                        cell.hyperlink = cell.value
                        cell.font = link_font
            
            full_path = os.path.abspath(filepath)
            print(f"💾 Файл сохранен: {full_path}")
            print(f"📝 Сохранено записей: {len(df)}")
            
            sites_found = sum(1 for r in self.results if r.get('Сайт_компании') not in [None, 'Не найден'])
            print(f"🌐 Найдено сайтов компаний: {sites_found}")
            
            return True, full_path
            
        except Exception as e:
            print(f"❌ Ошибка при сохранении: {e}")
            return False, None
    
    def run_parser(self, keywords, area=113, total_vacancies=None, per_keyword=None):
        print("🚀 ЗАПУСК ПАРСЕРА HH.RU")
        print("=" * 50)
        
        self.results = self.search_vacancies_hybrid(keywords, area, total_vacancies, per_keyword)
        
        if self.results:
            success, filepath = self.save_to_excel(keywords)
            
            if success:
                print("✅ ПАРСИНГ УСПЕШНО ЗАВЕРШЕН!")
                print(f"📊 Найдено вакансий: {len(self.results)}")
                
                keyword_stats = {}
                for result in self.results:
                    keyword = result.get('Ключевое_слово', 'Неизвестно')
                    keyword_stats[keyword] = keyword_stats.get(keyword, 0) + 1
                
                print("📈 Статистика по ключевым словам:")
                for keyword, count in keyword_stats.items():
                    print(f"   '{keyword}': {count} вакансий")
                
            return len(self.results), success, filepath
        else:
            print("❌ Вакансии не найдены")
            return 0, False, None

def get_region_id(region_name, api_client):
    if not region_name:
        return "113"
    
    regions = api_client.load_regions()
    if not regions:
        return "113"
    
    clean_name = region_name.lower().strip()
    
    if clean_name in regions:
        return regions[clean_name]
    
    for region_key in regions:
        if clean_name in region_key or region_key in clean_name:
            return regions[region_key]
    
    return "113"

class HHParserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HH.ru Parser")
        self.root.minsize(700, 600)
        self.center_window()
        
        self.parser = HHParser()
        self.setup_ui()
        self.load_regions_on_start()
    
    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def load_regions_on_start(self):
        self.progress_var.set("Загружаем регионы...")
        threading.Thread(target=self._load_regions_thread, daemon=True).start()
    
    def _load_regions_thread(self):
        try:
            regions = self.parser.api_client.load_regions()
            self.root.after(0, lambda: self.regions_loaded(regions))
        except Exception as e:
            self.root.after(0, lambda: self.regions_load_failed())
    
    def regions_loaded(self, regions):
        if regions:
            self.progress_var.set(f"Загружено {len(regions)} регионов")
    
    def regions_load_failed(self):
        self.progress_var.set("Ошибка загрузки регионов")
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(9, weight=1)
        
        title_label = ttk.Label(main_frame, text="Поиск вакансий на HH.ru", font=('Arial', 14, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        ttk.Label(main_frame, text="Ключевые слова для поиска:", font=('Arial', 10)).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.keywords_text = tk.Text(main_frame, height=5, width=70)
        self.keywords_text.grid(row=2, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E))
        self.keywords_text.insert(tk.END, "python\nменеджер\nаналитик\nразработчик")
        
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки поиска")
        settings_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        settings_frame.columnconfigure(1, weight=1)
        
        ttk.Label(settings_frame, text="Выберите регион:", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=5, pady=8)
        
        self.region_buttons_frame = ttk.Frame(settings_frame)
        self.region_buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.region_buttons_frame.columnconfigure(0, weight=1)
        self.region_buttons_frame.columnconfigure(1, weight=1)
        self.region_buttons_frame.columnconfigure(2, weight=1)
        
        self.region_var = tk.StringVar(value="113")
        
        self.russia_rb = ttk.Radiobutton(self.region_buttons_frame, text="Вся Россия", variable=self.region_var, value="113")
        self.russia_rb.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.moscow_rb = ttk.Radiobutton(self.region_buttons_frame, text="Москва", variable=self.region_var, value="1")
        self.moscow_rb.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        
        self.spb_rb = ttk.Radiobutton(self.region_buttons_frame, text="Санкт-Петербург", variable=self.region_var, value="2")
        self.spb_rb.grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(settings_frame, text="Или введите город вручную:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=8)
        self.custom_region_var = tk.StringVar()
        self.custom_region_entry = ttk.Entry(settings_frame, textvariable=self.custom_region_var, width=30)
        self.custom_region_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=8)
        
        if hasattr(self.custom_region_var, 'trace_add'):
            self.custom_region_var.trace_add('write', self.on_custom_region_change)
        else:
            self.custom_region_var.trace('w', self.on_custom_region_change)
        
        limits_frame = ttk.LabelFrame(main_frame, text="Лимиты вакансий")
        limits_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        limits_frame.columnconfigure(1, weight=1)
        
        self.limit_mode = tk.StringVar(value="none")
        
        ttk.Radiobutton(limits_frame, text="Без лимита", variable=self.limit_mode, value="none").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(limits_frame, text="Общее количество вакансий:", variable=self.limit_mode, value="total").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.total_vacancies_var = tk.StringVar(value="100")
        self.total_vacancies_entry = ttk.Entry(limits_frame, textvariable=self.total_vacancies_var, width=10)
        self.total_vacancies_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Radiobutton(limits_frame, text="На каждое ключевое слово:", variable=self.limit_mode, value="per_keyword").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.per_keyword_var = tk.StringVar(value="50")
        self.per_keyword_entry = ttk.Entry(limits_frame, textvariable=self.per_keyword_var, width=10)
        self.per_keyword_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        stats_frame = ttk.LabelFrame(main_frame, text="Статистика поиска")
        stats_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        self.stats_var = tk.StringVar(value="Вакансий найдено: 0")
        stats_label = ttk.Label(stats_frame, textvariable=self.stats_var, font=('Arial', 11, 'bold'))
        stats_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=8)
        
        self.progress_var = tk.StringVar(value="Загрузка регионов...")
        progress_label = ttk.Label(stats_frame, textvariable=self.progress_var, font=('Arial', 9))
        progress_label.grid(row=1, column=0, sticky=tk.W, padx=10, pady=4)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=15)
        
        self.parse_btn = ttk.Button(button_frame, text="Начать поиск", command=self.start_parsing, width=15)
        self.parse_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="Экспорт в Excel", command=self.export_to_excel, width=15)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    
    def on_custom_region_change(self, *args):
        custom_text = self.custom_region_var.get().strip()
        if custom_text:
            self.region_buttons_frame.grid_remove()
        else:
            self.region_buttons_frame.grid()
    
    def get_selected_region(self):
        if self.custom_region_var.get().strip():
            region_name = self.custom_region_var.get().strip()
            return get_region_id(region_name, self.parser.api_client)
        else:
            return self.region_var.get()
    
    def get_vacancies_limits(self):
        limit_mode = self.limit_mode.get()
        
        if limit_mode == "total":
            try:
                total = int(self.total_vacancies_var.get())
                return total, None
            except:
                return None, None
        elif limit_mode == "per_keyword":
            try:
                per_keyword = int(self.per_keyword_var.get())
                return None, per_keyword
            except:
                return None, None
        else:
            return None, None
    
    def start_parsing(self):
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        if not keywords_text:
            messagebox.showerror("Ошибка", "Введите ключевые слова")
            return
        
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        area = self.get_selected_region()
        total_vacancies, per_keyword = self.get_vacancies_limits()
        
        region_name = "Вся Россия"
        if area == "1":
            region_name = "Москва"
        elif area == "2":
            region_name = "Санкт-Петербург"
        elif self.custom_region_var.get().strip():
            region_name = self.custom_region_var.get().strip()
        
        limit_info = ""
        if total_vacancies:
            limit_info = f" (общий лимит: {total_vacancies})"
        elif per_keyword:
            limit_info = f" (на ключевое слово: {per_keyword})"
        
        self.stats_var.set("Идет поиск вакансий...")
        self.progress_var.set(f"Регион: {region_name}{limit_info}")
        
        thread = threading.Thread(target=self.run_parser, args=(keywords, area, total_vacancies, per_keyword))
        thread.daemon = True
        thread.start()
        
        self.parse_btn.config(state='disabled')
        self.progress.start()
    
    def run_parser(self, keywords, area, total_vacancies, per_keyword):
        try:
            vacancies_count, success, filepath = self.parser.run_parser(keywords, int(area), total_vacancies, per_keyword)
            self.root.after(0, lambda: self.parsing_completed(vacancies_count, success, filepath))
        except Exception as e:
            self.root.after(0, lambda: self.parsing_failed())
    
    def parsing_completed(self, vacancies_count, success, filepath):
        self.progress.stop()
        self.parse_btn.config(state='normal')
        
        self.stats_var.set(f"Вакансий найдено: {vacancies_count}")
        
        if success:
            self.progress_var.set("Поиск завершен!")
            
            if vacancies_count > 0:
                messagebox.showinfo("Успех", f"Найдено {vacancies_count} вакансий\nФайл сохранен: {os.path.basename(filepath)}")
            else:
                messagebox.showinfo("Результат", "Вакансии не найдены")
        else:
            self.progress_var.set("Ошибка при сохранении")
            messagebox.showerror("Ошибка", "Ошибка при сохранении данных")
    
    def parsing_failed(self):
        self.progress.stop()
        self.parse_btn.config(state='normal')
        self.stats_var.set("Вакансий найдено: 0")
        self.progress_var.set("Ошибка при поиске")
        messagebox.showerror("Ошибка", "Произошла ошибка при поиске")
    
    def export_to_excel(self):
        if not self.parser.results:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
        
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        default_filename = self.parser.generate_filename(keywords)
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=default_filename
        )
        
        if filename:
            success, filepath = self.parser.save_to_excel(keywords, filename)
            if success:
                messagebox.showinfo("Успех", f"Данные экспортированы в:\n{filepath}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HHParserGUI(root)
    
    try:
        root.mainloop()
    finally:
        pass