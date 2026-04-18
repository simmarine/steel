import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver

load_dotenv()
STEELDAILY_ID = os.getenv('STEELDAILY_ID', '')
STEELDAILY_PW = os.getenv('STEELDAILY_PW', '')
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
import csv

def get_last_crawled_date():
    """마지막 크롤링 날짜를 가져옵니다. 없으면 None을 반환합니다."""
    try:
        # steeldaily 폴더 안에 config 폴더 생성
        config_dir = os.path.join('steeldaily', 'config')
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
        config_dir = os.path.join('steeldaily', 'config')
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, 'last_crawled_date.txt')
        with open(config_file, 'w') as f:
            f.write(date_str)
    except Exception as e:
        print(f"마지막 크롤링 날짜 저장 실패: {e}")

def check_already_crawled(date_str):
    """해당 날짜의 크롤링이 이미 완료되었는지 확인합니다."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        file_path = os.path.join('steeldaily', 
                                str(date_obj.year),
                                f"{date_obj.month:02d}",
                                f"{date_obj.day:02d}",
                                f"steeldaily_{date_str}.csv")
        return os.path.exists(file_path)
    except ValueError:
        return False

def create_date_directory(date_str):
    """날짜 문자열을 기반으로 년/월/일 폴더 구조를 생성합니다."""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        
        year_dir = str(date_obj.year)
        month_dir = f"{date_obj.month:02d}"
        day_dir = f"{date_obj.day:02d}"
        
        base_path = os.path.join('steeldaily', year_dir, month_dir, day_dir)
        os.makedirs(base_path, exist_ok=True)
        
        return base_path
    except ValueError as e:
        print(f"날짜 형식 오류: {e}")
        return None

def save_article_csv(articles_data, date_str):
    """기사들을 날짜별 폴더에 CSV 파일로 저장합니다."""
    if not articles_data:  # 데이터가 없으면 저장하지 않음
        return False

    dir_path = create_date_directory(date_str)
    if not dir_path:
        return False
    
    file_path = os.path.join(dir_path, f"steeldaily_{date_str}.csv")
    
    try:
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['Link', 'Date', 'Title', 'Content'])
            writer.writeheader()
            writer.writerows(articles_data)
            
        print(f"저장 완료: {file_path}")
        return True
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return False

def handle_alert(driver):
    """예상치 못한 경고를 처리합니다."""
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
        print("경고를 수락했습니다.")
    except:
        print("경고를 찾을 수 없습니다.")

def login(driver):
    """웹사이트에 로그인합니다."""
    driver.get('https://www.steeldaily.co.kr/')
    
    login_button_xpath = '//*[@class="user-point"]'
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, login_button_xpath))
    ).click()
    
    user_id_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'user_id'))
    )
    user_pw_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.ID, 'user_pw'))
    )
    
    user_id_field.clear()
    user_id_field.send_keys(STEELDAILY_ID)
    user_pw_field.clear()
    user_pw_field.send_keys(STEELDAILY_PW)
    
    loginpage_button_xpath = '//*[@class="button expanded large user-bg mary-25"]'
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, loginpage_button_xpath))
    ).click()
    
    user_pw_field.send_keys(Keys.RETURN)
    handle_alert(driver)

def crawl_article(driver, link):
    """링크를 통해 기사의 내용을 크롤링합니다."""
    driver.get(link)
    time.sleep(2)
    
    try:
        title_tag = driver.find_element(By.CSS_SELECTOR, 'h3.heading')
        title = title_tag.text.strip()
    except: 
        title = "제목 없음"
    
    try:
        content_tag = driver.find_element(By.CSS_SELECTOR, 'article#article-view-content-div')
        paragraphs = content_tag.find_elements(By.TAG_NAME, 'p')
        content = ' '.join([para.text.strip() for para in paragraphs])
    except:
        content = "내용 없음"
    
    return title, content

def crawl_article_list(driver, page):
    """주어진 페이지의 기사 목록을 크롤링합니다."""
    base_url = 'http://www.steeldaily.co.kr'
    section_url = '/news/articleList.html?view_type=sm'
    news_url = f"{base_url}{section_url}&page={page}"
    
    try:
        driver.get(news_url)
    except:
        handle_alert(driver)
        driver.get(news_url)
    
    time.sleep(2)
    
    articles = driver.find_elements(By.CSS_SELECTOR, 'ul.type2 > li')
    article_data = []
    for article in articles:
        try:
            link_tag = article.find_element(By.CSS_SELECTOR, 'h4.titles a')
            link = link_tag.get_attribute('href')
            date_tag = article.find_element(By.CSS_SELECTOR, 'span.byline em')
            date_text = date_tag.text.strip()
            
            # 날짜 추출 (시간 제외)
            date = date_text.split()[0]  # "YYYY-MM-DD" 부분만 추출
            
            article_data.append({
                'Link': link,
                'Date': date
            })
        except Exception as e:
            print(f"기사 정보 추출 중 오류 발생: {e}")
            continue
    
    return article_data

def crawl_all_pages(driver):
    """마지막 크롤링 날짜 이후의 기사를 크롤링하고 CSV 파일로 저장합니다."""
    if not os.path.exists('steeldaily'):
        os.makedirs('steeldaily')
    
    # 현재 날짜와 마지막 크롤링 날짜 확인
    current_date = datetime.now().strftime('%Y-%m-%d')
    last_crawled_date = get_last_crawled_date()
    
    if last_crawled_date:
        print(f"마지막 크롤링 날짜: {last_crawled_date}")
    else:
        print("이전 크롤링 기록이 없습니다. 오늘부터 크롤링을 시작합니다.")
        last_crawled_date = '2000-01-01'  # 매우 이전 날짜로 설정
    
    page = 1
    date_articles = {}  # 날짜별 기사 저장
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
            
            # 아직 크롤링되지 않은 날짜의 기사만 처리
            if not check_already_crawled(date):
                link = item['Link']
                title, content = crawl_article(driver, link)
                
                article_info = {
                    'Date': date,
                    'Title': title,
                    'Content': content,
                    'Link': link
                }
                
                if date not in date_articles:
                    date_articles[date] = []
                date_articles[date].append(article_info)
                print(f"기사 추가 완료: {date} - {title}")
                
                # 최신 날짜 업데이트
                if date > newest_date_crawled:
                    newest_date_crawled = date
            else:
                print(f"{date} 날짜는 이미 크롤링되어 있어 스킵합니다.")
        
        page += 1
        print(f"{page} 페이지 크롤링 완료.")
        time.sleep(1)
    
    # 수집된 데이터 저장
    for date, articles in date_articles.items():
        if articles:  # 데이터가 있는 경우에만 저장
            save_article_csv(articles, date)
    
    # 가장 최근에 크롤링한 날짜 저장
    if date_articles:  # 새로 크롤링된 데이터가 있는 경우에만 업데이트
        save_last_crawled_date(newest_date_crawled)
        print(f"마지막 크롤링 날짜를 {newest_date_crawled}로 업데이트했습니다.")

def setup_driver():
    """드라이버 설정을 수행합니다."""
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def main_job():
    """메인 작업을 실행합니다."""
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