import time
import json
import sys
from .utils import *
from collections import namedtuple
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


now = datetime.now()
date_time_format = now.strftime("%Y-%m-%d_%H-%M-%S")

JobListingSearchResult = namedtuple(
    "JobListingSearchResult",
    [
        "typename",
        "atsSource",
        "autoPosted",
        "currentUserApplied",
        "description",
        "id",
        "jobType",
        "lastRespondedAt",
        "liveStartAt",
        "primaryRoleTitle",
        "remote",
        "reposted",
        "slug",
        "title",
        "compensation",
        "usesEstimatedSalary",
        "company_name",
        "company_high_concept",
    ],
)


class Companies:
    def __init__(self, **kwargs):
        self.query = kwargs.get("query", [])

    def get_companies(self, query):
        all_job_listings = []
        for i in range(1, 100):
            variables = {
                "filterConfigurationInput": {
                    "page": i,
                    "remoteCompanyLocationTagIds": ["1692", "1693"],
                    "roleTagIds": ["14726"],
                    "skillTagIds": ["14775", "139914", "17000"],
                    "equity": {"min": None, "max": None},
                    "excludedKeywords": ["web3", "crypto", "cryptocurrency"],
                    "jobTypes": ["full_time"],
                    "remotePreference": "REMOTE_OPEN",
                    "salary": {"min": None, "max": None},
                    "yearsExperience": {"max": 2, "min": None},
                },
            }

            if query:
                variables["filterConfigurationInput"]["keywords"] = query

            payload = {
                "operationName": "JobSearchResultsX",
                "variables": variables,
                "extensions": {
                    "operationId": "tfe/b898ee628dd3385e1b8c467e464a0261ad66c478eda6e21e10566b0ca4ccf1e9"
                },
            }

            js_script = """
var callback = arguments[0];
var xhr = new XMLHttpRequest();
xhr.open('POST', 'https://wellfound.com/graphql?fallbackAOR=talent', true);
xhr.setRequestHeader('Content-Type', 'application/json');
xhr.setRequestHeader('Accept', '*/*');
xhr.setRequestHeader('Accept-Language', 'en-US,en;q=0.9');
xhr.setRequestHeader('Apollographql-Client-Name', 'talent-web');
xhr.setRequestHeader('Origin', 'https://wellfound.com');
xhr.setRequestHeader('Referer', 'https://wellfound.com/jobs');
xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
xhr.onreadystatechange = function() {
    if (xhr.readyState == 4) {
        if (xhr.status == 200) {
            callback(xhr.responseText);
        } else {
            console.error('Error with status code:', xhr.status);
            callback(JSON.stringify({error: true, status: xhr.status, statusText: xhr.statusText, response: xhr.responseText}));
        }
    }
};
xhr.send(JSON.stringify(%s));
""" % json.dumps(payload)

            response = self.driver.execute_async_script(js_script)

            time.sleep(5)

            if isinstance(response, str):
                if response.startswith("Error:") or response.startswith('{"error"'):
                    print(f"Request failed: {response[:500]}")
                    break
                try:
                    response = json.loads(response)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse response as JSON: {e}")
                    print(f"Raw response: {response[:500]}")
                    break

            job_listings = list()
            try:
                startups = response["data"]["talent"]["jobSearchResults"]["startups"]["edges"]
            except (KeyError, TypeError) as e:
                print(f"Unexpected response structure: {e}")
                print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else type(response)}")
                break

            for j in range(0, len(startups)):
                startup_info = startups[j]["node"]
                startup_job_listings = startup_info["highlightedJobListings"]

                for job in startup_job_listings:
                    job_listings.append(
                        JobListingSearchResult(
                            job["__typename"],
                            job["atsSource"],
                            job["autoPosted"],
                            job["currentUserApplied"],
                            job["description"],
                            job["id"],
                            job["jobType"],
                            job["lastRespondedAt"],
                            job["liveStartAt"],
                            job["primaryRoleTitle"],
                            job["remote"],
                            job["reposted"],
                            job["slug"],
                            job["title"],
                            job["compensation"],
                            job["usesEstimatedSalary"],
                            startup_info.get("name", ""),
                            startup_info.get("highConcept", ""),
                        )
                    )

            for job in job_listings:
                print(f"{job.company_name} | {job.title} | {job.compensation} | {job.id}")

            all_job_listings.extend(job_listings)

            response_json = json.dumps(response, indent=4)

            with open(f"response_{date_time_format}_page_{i}.json", "w") as file:
                print("writing to file...")
                file.write(response_json)

            has_next_page = response["data"]["talent"]["jobSearchResults"]["hasNextPage"]
            if not has_next_page:
                break

        for remaining in range(10, 0, -1):
            sys.stdout.write("\rsleeping in {:2d} seconds...".format(remaining))
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\rComplete!                       \n")

        return all_job_listings

    def browse_jobs(self, num_scrolls=5, answer_fn=None):
        wait = WebDriverWait(self.driver, 10)

        if "/jobs" not in self.driver.current_url:
            self.driver.get(f"{Base.URL}/jobs")
            time.sleep(5)

        print("Scrolling to load jobs...")
        for i in range(num_scrolls):
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            time.sleep(2)
            print(f"  Scroll {i + 1}/{num_scrolls}")

        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(1)

        job_cards = self.driver.find_elements(
            By.CSS_SELECTOR, ".styles_component__Ey28k"
        )
        print(f"Found {len(job_cards)} job cards\n")

        results = []
        for i, card in enumerate(job_cards, 1):
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'})", card
                )
                time.sleep(1)

                link_text = card.text.strip().split("\n")[0]
                print(f"[{i}/{len(job_cards)}] Clicking job card: {link_text}")
                card.click()
                time.sleep(3)

                

                title = ""
                try:
                    title = self.driver.find_element(By.CSS_SELECTOR, "h1").text.strip()
                except NoSuchElementException:
                    title = link_text

                company_name = ""
                for sel in ['a[href*="/company/"] h2', 'a[href*="/company/"]', "h2"]:
                    try:
                        el = self.driver.find_element(By.CSS_SELECTOR, sel)
                        if el.text.strip():
                            company_name = el.text.strip()
                            break
                    except NoSuchElementException:
                        continue

                description = self.driver.find_element(By.TAG_NAME, "body").text

                print(f"  Company: {company_name}")
                print(f"  Title: {title}")
                print(f"  Description: {description[:100]}...")

                answer = ""
                if answer_fn:
                    print("  Generating answer...")
                    answer = answer_fn(company_name, title, description)
                    print(f"  Answer: {answer[:120]}...")

                    try:
                        textarea = wait.until(EC.presence_of_element_located(
                            (By.CSS_SELECTOR, ".styles-module_component__2Y90D")
                        ))
                        textarea.clear()
                        textarea.send_keys(answer)
                        print("  Filled textarea.")
                        time.sleep(2)
                    except TimeoutException:
                        print("  Could not find textarea.")

                results.append({
                    "title": title,
                    "company_name": company_name,
                    "description": description,
                    "url": self.driver.current_url,
                    "answer": answer,
                })

                try:
                    apply_btn = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".styles_component__AUM9C")
                    ))
                    print(f"  Clicking apply/view button...")
                    apply_btn.click()
                    time.sleep(3)
                except TimeoutException:
                    print("  Could not find button, skipping.")
                    self.driver.back()
                    time.sleep(2)
                    continue

                try:
                    close_btn = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, ".styles_closeButton__rY4C2")
                    ))
                    print("  Closing...")
                    close_btn.click()
                    time.sleep(2)
                except TimeoutException:
                    self.driver.back()
                    time.sleep(2)

            except Exception as e:
                print(f"  Error: {e}")
                try:
                    close_btn = self.driver.find_element(
                        By.CSS_SELECTOR, ".styles_closeButton__rY4C2"
                    )
                    close_btn.click()
                    time.sleep(2)
                except NoSuchElementException:
                    pass

        return results
