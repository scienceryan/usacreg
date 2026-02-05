import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Helper Functions ---

def activate_discipline(driver, discipline_name):
    """Dynamically clicks the discipline tab based on the provided name."""
    try:
        # We use a normalized XPath to find the tab matching the name
        xpath = f"//div[contains(@class, 'nav-item') and normalize-space()='{discipline_name}']"
        discipline_tab = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        discipline_tab.click()
        # Give the UI a moment to swap the athlete list
        time.sleep(1.5) 
    except Exception as e:
        print(f"Warning: Could not click discipline '{discipline_name}': {e}")

# --- Initialization ---

event_id = input("Enter the USAC Event ID (e.g., 383): ").strip()
url = f"https://usac.results.info/event/{event_id}/registrations"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
driver.get(url)

# --- Discovery: Find the Nav Rows ---
print("Scanning page for navigation menus...")

# Wait for the general navigation container
WebDriverWait(driver, 15).until(
    EC.presence_of_element_located((By.CLASS_NAME, "rs-event-nav"))
)

# Get all navigation rows (Row 1 is usually Category, Row 2 is Discipline)
nav_rows = driver.find_elements(By.CLASS_NAME, "rs-event-nav")

if len(nav_rows) < 1:
    print("Error: Could not find any 'rs-event-nav' rows.")
    # Fallback: Try a generic selector
    nav_rows = driver.find_elements(By.CSS_SELECTOR, ".nav.nav-pills")

# --- The Loop ---
# We assume nav_rows[0] is Category and nav_rows[1] is Discipline
category_tabs = nav_rows[0].find_elements(By.CLASS_NAME, "nav-item")
category_count = len(category_tabs)
print(f"Discovered {category_count} categories.")


all_registrations = []
for c_index in range(category_count):
    # Re-fetch rows to prevent StaleElementReferenceException
    current_nav_rows = driver.find_elements(By.CLASS_NAME, "rs-event-nav")
    c_tabs = current_nav_rows[0].find_elements(By.CLASS_NAME, "nav-item")
    
    category_name = c_tabs[c_index].text.strip()
    print(f"\nSwitching to Category: {category_name}")
    c_tabs[c_index].click()
    time.sleep(0.1)

    # Re-fetch the second row for Disciplines
    # Note: Some events might only have ONE row if there's only one discipline
    if len(current_nav_rows) > 1:
        d_tabs = current_nav_rows[1].find_elements(By.CLASS_NAME, "nav-item")
        discipline_names = [d.text.strip() for d in d_tabs if d.text.strip()]
    else:
        # Fallback if there is no second row (e.g., Only Lead is available)
        discipline_names = ["General"] 

    for d_name in discipline_names:
        if d_name != "General":
            print(f"  Activating Discipline: {d_name}")
            activate_discipline(driver, d_name)
        
        # Now Scrape...
        athlete_rows = driver.find_elements(By.CSS_SELECTOR, "div.athlete-container")
        print(f"    Found {len(athlete_rows)} athletes.")
        # ... (rest of your scraping logic)
        # 3. Scrape the athletes 
        athlete_rows = driver.find_elements(By.CSS_SELECTOR, "div.athlete-container")
            
        for row in athlete_rows:
            try:
                name_link = row.find_element(By.CLASS_NAME, "r-name")
                name = name_link.text.strip()
                athlete_id = name_link.get_attribute("href").split("/")[-1]

                try:
                    team = row.find_element(By.CLASS_NAME, "r-name-sub").text.strip()
                except:
                    team = "No Team"

                status = row.find_element(By.CLASS_NAME, "athlete-registration-status").text.strip()
                    
                all_registrations.append({
                     "Athlete ID": athlete_id,
                     "Name": name,
                     "Team": team,
                     "Category": category_name,
                     "Discipline": d_name,
                     "Status": status
                })
            except Exception as e:
                print(f"Warning: Could not scrape athlete row: {e}")


# --- Final Processing and Summary ---

    if all_registrations:
        df = pd.DataFrame(all_registrations).drop_duplicates()

        print("\n" + "="*40)
        print("   SUMMARY: ATHLETE COUNTS")
        print("="*40)

        # High level count
        print("\n[Counts by Discipline and Category]")
        print(df.groupby(['Discipline', 'Category']).size())

        # Detailed Team breakdown
        print("\n[Detailed Team Breakdown]")
        team_summary = df.groupby(['Discipline', 'Category', 'Team']).size().reset_index(name='Count')
        # Sort by Count descending so the biggest teams are at the top
        team_summary = team_summary.sort_values(by=['Discipline', 'Category', 'Count'], ascending=[True, True, False])
        print(team_summary.to_string(index=False))
        
        # Export
        csv_name = f"usac_event_{event_id}_registrations.csv"
        df.to_csv(csv_name, index=False)
        print(f"\nSUCCESS: {len(df)} unique entries in {csv_name}")

    else:
        print("\n[!] No registration data found.")



driver.quit()