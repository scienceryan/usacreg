# USA Climbing Event Registration Scraper

A Python-based web scraper that automates the collection of athlete registration data from the USA Climbing results portal. It navigates through category and discipline tabs to compile a comprehensive list of athletes, their teams, and their registration status.

## 🚀 Features
- **Dynamic Navigation:** Automatically clicks through Gender/Category and Discipline (Lead, Speed, Boulder) tabs.
- **Data Extraction:** Collects Athlete ID, Name, Team, Category, Discipline, and Status.
- **Reporting:** Generates a console summary of athlete counts by team and discipline.
- **CSV Export:** Saves all scraped data into a clean, deduplicated CSV file.
- **Error Handling:** Includes a debug mode that captures page source if no data is found.

## 🛠️ Requirements
- Python 3.10+
- [Google Chrome](https://www.google.com/chrome/)
- Selenium & WebDriver Manager
- Pandas

## 📦 Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/scienceryan/usacreg.git](https://github.com/scienceryan/usacreg.git)
   cd usacreg