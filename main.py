import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup
import process.constants as const


def initialize_driver():
    service = Service(const.CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=service, options=options)
    driver.maximize_window()
    return driver


def login(driver):
    driver.get(const.BASE_URL)
    wait = WebDriverWait(driver, 10)

    linkedin_button = wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "nav__button-secondary.btn-md.btn-secondary-emphasis")))
    linkedin_button.click()

    login_email = wait.until(EC.visibility_of_element_located((By.ID, "username")))
    login_email.send_keys(const.EMAIL)

    login_password = wait.until(EC.visibility_of_element_located((By.ID, "password")))
    login_password.send_keys(const.PASSWORD)

    login_next_button = wait.until(
        EC.element_to_be_clickable((By.CLASS_NAME, "btn__primary--large.from__button--floating")))
    login_next_button.click()

    time.sleep(15)


def search_url(driver):
    # Edit the search URL here
    driver.get(const.SEARCH_URL)


def scrape_companies(driver, companies_dict, max_pages=10):
    wait = WebDriverWait(driver, 10)
    search_url(driver)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'ember-view   jobs-search-results__list-item occludable-update p0 relative scaffold-layout__list-item')))

    page_count = 0
    while page_count < max_pages:
        page_count += 1
        print(f"Scraping page {page_count}")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        company_cards = soup.find_all('li', {'class': 'ember-view   jobs-search-results__list-item occludable-update p0 relative scaffold-layout__list-item'})

        for company in company_cards:
            try:
                company_link = company.find('a', {'class': 'disabled ember-view job-card-container__link job-card-list__title job-card-list__title--link'})['href']
                driver.get(company_link)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'job-view-layout jobs-details')))

                company_soup = BeautifulSoup(driver.page_source, 'html.parser')
                location_elements = company_soup.find_all('div', {'class': 'tvm__text tvm__text--low-emphasis'})

                if len(location_elements) >= 2 and 'Hyderabad' in location_elements[1].text:
                    company_name_element = company_soup.find('div', {'class': 'job-details-jobs-unified-top-card__company-name'})
                    company_name = company_name_element.text.strip() if company_name_element else 'Not specified'
                    print(company_name)
                    if company_name in companies_dict:
                        print(f"Skipping already present company: {company_name}")
                        driver.back()
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'ember-view   jobs-search-results__list-item occludable-update p0 relative scaffold-layout__list-item')))
                        continue

                    job_element = company_soup.find('div', {'class': 'display-flex justify-space-between flex-wrap mt2'})
                    job_title = job_element.text.strip() if job_element else 'Not specified'
                    print(job_title)

                    description_element = company_soup.find("li", {'class': 'job-details-jobs-unified-top-card__job-insight job-details-jobs-unified-top-card__job-insight--highlight'})
                    job_description = description_element.text.strip() if description_element else 'Not specified'
                    print(job_description)

                    skills_element = company_soup.find("button", {'class': 'job-details-jobs-unified-top-card__job-insight-text-button'})
                    skills_needed = skills_element.text.strip() if skills_element else 'Not specified'
                    print(skills_needed)

                    time.sleep(5)
                    driver.back()
                    time.sleep(5)

                    companies_dict[company_name] = {
                        'Company Name': company_name,
                        'Job Title': job_title,
                        'Job Description': job_description,
                        'Skills Required': skills_needed
                    }

                    print(f"Added company: {company_name}")

                driver.back()
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'reusable-search__result-container')))

            except Exception as e:
                print(f"An error occurred while processing company: {e}")
                continue

        save_to_csv(companies_dict, 'company_data.csv')
        time.sleep(5)
        scroll_and_click_next(driver, wait)


def save_to_csv(companies_dict, filename):
    fieldnames = ['Company Name', 'Job Title', 'Job Description', 'Skills Required']
    existing_companies = {}

    # Read existing company names into a dictionary
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_companies[row['Company Name']] = row
    except FileNotFoundError:
        print(f"{filename} not found. A new file will be created.")

    # Update existing companies and add new companies
    for company_name, company_info in companies_dict.items():
        if company_name in existing_companies:
            existing_companies[company_name].update(company_info)
            print(f"Updating company: {company_name}")
        else:
            existing_companies[company_name] = company_info
            print(f"Adding new company: {company_name}")

    # Write all data back to the CSV file
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for company_info in existing_companies.values():
            writer.writerow(company_info)

    print(f"Data has been written to {filename}")


def scroll_and_click_next(driver, wait):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    try:
        next_button = driver.find_element(By.XPATH, '//button[@aria-label="View next page"]')
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="View next page"]')))
        next_button.click()
        print("Navigating to next page")
        time.sleep(5)
    except TimeoutException:
        print("No more pages")


def main():
    driver = initialize_driver()
    companies_dict = {}

    try:
        login(driver)
        scrape_companies(driver, companies_dict)
        print("Done Scraping!")
    except TimeoutException as e:
        print(f"Timeout occurred: {e}")
    except NoSuchElementException as e:
        print(f"Element not found: {e}")
    except WebDriverException as e:
        print(f"WebDriverException occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
