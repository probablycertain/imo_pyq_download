import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
import time
from urllib.parse import urljoin

def download_pdf(url, filename, download_folder):
    """Download a PDF file to the specified folder"""
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        filepath = os.path.join(download_folder, filename)
        with open(filepath, 'wb') as f:
            f.write(response.content)
        print(f"✓ Successfully downloaded: {filename}")
        return True
    except Exception as e:
        print(f"✗ Failed to download {filename}: {str(e)}")
        return False

def download_problem_pdf(session, year, base_url, download_folder):
    """
    Download the problem PDF for a given year by submitting the form with English selected
    The form sets DLFile to the language option value (e.g., "2025/eng")
    """
    try:
        print(f"Fetching English problems for year {year}...")
        
        # Construct the DLFile value for English
        dl_file = f"{year}/eng"
        
        # Prepare form data
        form_data = {
            'DLFile': dl_file
        }
        
        # Submit POST request to problems.aspx
        download_url = f"{base_url}problems.aspx"
        response = session.post(download_url, data=form_data, timeout=30, stream=True)
        
        # Check if we got a PDF back
        content_type = response.headers.get('content-type', '')
        if 'application/pdf' in content_type or response.status_code == 200:
            # Check if response has content
            if len(response.content) > 0:
                filename = f"IMO_{year}_Problems_English.pdf"
                filepath = os.path.join(download_folder, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Successfully downloaded: {filename}")
                return True
            else:
                print(f"✗ Empty response for year {year}")
                return False
        else:
            print(f"✗ Could not download problems for year {year} (not a PDF response)")
            return False
            
    except Exception as e:
        print(f"✗ Failed to download problems for year {year}: {str(e)}")
        return False

def main():
    # Setup
    base_url = "https://www.imo-official.org/"
    problems_url = "https://www.imo-official.org/problems.aspx"
    download_folder = str(Path.home() / "Downloads")
    
    print(f"Downloading IMO PDFs to: {download_folder}\n")
    
    # Create a session to maintain cookies and state
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Referer': problems_url
    })
    
    # Fetch the main problems page to establish session
    try:
        response = session.get(problems_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching main page: {str(e)}")
        return
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table with problems
    table = soup.find('table')
    if not table:
        print("Could not find problems table on the page")
        return
    
    rows = table.find_all('tr')[1:]  # Skip header row
    
    downloaded = 0
    failed = 0
    
    print("="*60)
    print("PHASE 1: Downloading Shortlist PDFs (2006-2024)")
    print("="*60 + "\n")
    
    # First, download all Shortlist PDFs (2006-2024)
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        
        # Extract year
        year_link = cells[0].find('a')
        if not year_link:
            continue
        
        year = year_link.text.strip()
        
        # Check for Shortlist PDF (column 4, for years 2006-2024)
        shortlist_cell = cells[3]
        shortlist_link = shortlist_cell.find('a', string='PDF')
        
        if shortlist_link:
            # Download Shortlist PDF
            pdf_href = shortlist_link.get('href')
            pdf_url = urljoin(base_url, pdf_href)
            filename = f"IMO_{year}_Shortlist.pdf"
            
            if download_pdf(pdf_url, filename, download_folder):
                downloaded += 1
            else:
                failed += 1
            
            time.sleep(1)  # Be polite to the server
    
    print("\n" + "="*60)
    print("PHASE 2: Downloading Problem PDFs (1959-2025)")
    print("="*60 + "\n")
    
    # Now download the problem PDFs for years 1959-2025
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        
        # Extract year
        year_link = cells[0].find('a')
        if not year_link:
            continue
        
        year = year_link.text.strip()
        year_num = int(year)
        
        # Only process years 1959-2025
        if year_num < 1959 or year_num > 2025:
            continue
        
        # Check if there's a language selector in column 2
        language_cell = cells[1]
        select = language_cell.find('select')
        
        # Check if English option exists (either as dropdown or text)
        has_english = False
        
        if select:
            # Has dropdown - check for English option
            english_option = select.find('option', value=lambda x: x and x.endswith('/eng'))
            if english_option:
                has_english = True
        elif 'English' in language_cell.get_text():
            # Has "English" text (pre-selected)
            has_english = True
        
        if has_english:
            if download_problem_pdf(session, year, base_url, download_folder):
                downloaded += 1
            else:
                failed += 1
            
            time.sleep(1)  # Be polite to the server
        else:
            print(f"⊘ Skipping year {year} - English not available")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Download Summary:")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()