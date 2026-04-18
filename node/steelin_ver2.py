import time
import os
import json  # 추가: JSON 출력을 위해
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver

load_dotenv()
STEELIN_ID = os.getenv('STEELIN_ID', '')
STEELIN_PW = os.getenv('STEELIN_PW', '')
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

def get_last_crawled_date():
    """마지막 크롤링 날짜를 가져옵니다. 없으면 None을 반환합니다."""
    try:
        config_dir = os.path.join('steelin', 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, 'last_crawled_date.txt')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return f.read().strip()
        return None
    except Exception as e:
        print(f"마지막 크롤링 날짜 읽기 실패: {e}")
        return None

def save_last_crawled_date(date_str):
    """마지막 크롤링 날짜를 저장합니다."""
    try:
        config_dir = os.path.join('steelin', 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, 'last_crawled_date.txt')
        with open(config_file, 'w') as f:
            f.write(date_str)
    except Exception as e:
        print(f"마지막 크롤링 날짜 저장 실패: {e}")

def check_already_crawled(date_str):
    return False

def handle_alert(driver):
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
        print("경고를 수락했습니다.", file=sys.stderr)  # stderr로 변경
    except:
        pass

def login(driver):
    """웹사이트에 로그인합니다."""
    print("로그인 시도 중...", file=sys.stderr)
    driver.get('https://www.steelin.co.kr/member/login.html')

    try:
        user_id_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, 'user_id'))
        )
        user_pw_field = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.ID, 'user_pw'))
        )
        
        user_id_field.clear()
        user_id_field.send_keys(STEELIN_ID)
        user_pw_field.clear()
        user_pw_field.send_keys(STEELIN_PW)
        
        loginpage_button_xpath = '//*[@class="button expanded large user-bg"]'
        WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, loginpage_button_xpath))
        ).click()
        print("로그인 성공!", file=sys.stderr)

        handle_alert(driver)
    except Exception as e:
        print(f"로그인 실패: {e}", file=sys.stderr)


def crawl_article(driver, link):
    """링크를 통해 기사의 내용을 크롤링합니다."""
    driver.get(link)
    time.sleep(2)
    
    try:
        title_tag = driver.find_element(By.CSS_SELECTOR, 'div.article-head-title')
        title = title_tag.text.strip()
    except: 
        title = "제목 없음"
    
    try:
        content_tag = driver.find_element(By.CSS_SELECTOR, 'div#article-view-content-div')
        paragraphs = content_tag.find_elements(By.TAG_NAME, 'p')
        content = ' '.join([para.text.strip() for para in paragraphs])
    except:
        content = "내용 없음"
    
    return title, content

def crawl_article_list(driver, page):
    """주어진 페이지의 기사 목록을 크롤링합니다."""
    base_url = 'https://www.steelin.co.kr'
    section_url = '/news/articleList.html?view_type=sm'
    news_url = f"{base_url}{section_url}&page={page}"
    print(f"페이지 URL: {news_url}", file=sys.stderr)

    try:
        driver.get(news_url)
    except:
        handle_alert(driver)
        driver.get(news_url)
    
    time.sleep(2)
    
    articles = driver.find_elements(By.CSS_SELECTOR, '.list-block')
    print(f"발견된 기사 수: {len(articles)}", file=sys.stderr)

    article_data = []
    for article in articles:
        try:
            link_tag = article.find_element(By.CSS_SELECTOR, '.list-titles a')
            link = link_tag.get_attribute('href')
            date_tag = article.find_element(By.CSS_SELECTOR, '.list-dated')
            date_text = date_tag.text.strip()
            
            date_parts = date_text.split('|')
            if len(date_parts) >= 3:
                date_time = date_parts[2].strip()
                date = date_time.split()[0]
                
                article_data.append({
                    'Link': link,
                    'Date': date
                })
                print(f"기사 수집: {date} - {link}", file=sys.stderr)
        except Exception as e:
            print(f"기사 정보 추출 중 오류 발생: {e}", file=sys.stderr)
            continue
    
    return article_data


def crawl_all_pages(driver):
    """마지막 크롤링 날짜 이후의 기사를 크롤링하고 JSON으로 출력합니다."""
    current_date = datetime.now().strftime('%Y-%m-%d')
    last_crawled_date = get_last_crawled_date()
    
    if last_crawled_date:
        print(f"마지막 크롤링 날짜: {last_crawled_date}", file=sys.stderr)  # stderr로 로그 출력
    else:
        print("이전 크롤링 기록이 없습니다. 오늘부터 크롤링을 시작합니다.", file=sys.stderr)  # stderr로 로그 출력
        last_crawled_date = '2000-01-01'  # 매우 이전 날짜로 설정
    
    page = 1
    all_articles = []  # 모든 기사 데이터를 저장할 리스트
    found_old_article = False
    newest_date_crawled = last_crawled_date  # 새로 크롤링한 기사 중 가장 최신 날짜
    
    while not found_old_article:
        data = crawl_article_list(driver, page)
        if not data:
            break
        
        for item in data:
            date = item['Date']
            
            # 마지막 크롤링 날짜 이전의 기사를 만나면 종료
            if date <= last_crawled_date:
                found_old_article = True
                break
            
            link = item['Link']
            title, content = crawl_article(driver, link)
            
            article_info = {
                'Date': date,
                'Title': title,
                'Content': content,
                'Link': link,
                'label': 0  # 새로운 컬럼 label 추가
            }
            
            all_articles.append(article_info)
            print(f"기사 추가 완료: {date} - {title}", file=sys.stderr)  # stderr로 로그 출력
            
            # 최신 날짜 업데이트
            if date > newest_date_crawled:
                newest_date_crawled = date
        
        page += 1
        print(f"{page} 페이지 크롤링 완료.", file=sys.stderr)  # stderr로 로그 출력
        time.sleep(1)
    
    # 가장 최근에 크롤링한 날짜 저장
    if all_articles:  # 새로 크롤링된 데이터가 있는 경우에만 업데이트
        save_last_crawled_date(newest_date_crawled)
        print(f"마지막 크롤링 날짜를 {newest_date_crawled}로 업데이트했습니다.", file=sys.stderr)  # stderr로 로그 출력
    
    # 모든 기사 데이터를 JSON으로 출력
    print(json.dumps(all_articles, ensure_ascii=False))


def setup_driver():
    """드라이버 설정을 수행합니다."""
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # 브라우저 창을 띄우지 않음
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def main_job():
    """메인 작업을 실행합니다."""
    # 표준 출력 스트림을 UTF-8로 설정
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    
    driver = setup_driver()
    try:
        login(driver)
        crawl_all_pages(driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    try:
        main_job()
    except KeyboardInterrupt:
        print("프로그램이 사용자에 의해 중단되었습니다.")
