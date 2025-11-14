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

def extract_language_selectors(soup):
    """
    Extract all language selector names and their default values from the page
    Returns a dictionary like {'language2025': '2025/afr', 'language2024': '2024/afr', ...}
    Only includes years that actually have a dropdown selector on the page.
    """
    selectors = {}
    
    # Find all select elements with names starting with 'language'
    for select in soup.find_all('select'):
        name = select.get('name')
        if name and name.startswith('language'):
            # Get the selected option value (the one with selected="selected")
            selected_option = select.find('option', selected=True)
            if selected_option:
                selectors[name] = selected_option.get('value')
            else:
                # If no option is marked as selected, get the first one
                first_option = select.find('option')
                if first_option:
                    selectors[name] = first_option.get('value')
    
    print(f"DEBUG: Found selectors for years: {[name.replace('language', '') for name in selectors.keys()]}")
    return selectors

def download_problem_pdf(session, year, language_selectors, base_url, download_folder):
    """
    Download the problem PDF for a given year by submitting the form with English selected
    Includes all language selector values as required by the form.
    Only includes selectors that exist on the page (years with dropdowns).
    """
    try:
        print(f"Fetching English problems for year {year}...")
        
        # Construct the DLFile value for English
        dl_file = f"{year}/eng"
        
        # IMPORTANT: DLFile must be first in the form data
        # Create form_data with DLFile first, then add all language selectors
        form_data = {'DLFile': dl_file}
        
        # Add all the language selectors (with their default values)
        # This only includes years that have dropdowns
        for key, value in language_selectors.items():
            form_data[key] = value
        
        # Update the language selector for this specific year to English
        # (only if this year has a dropdown selector)
        year_selector_name = f"language{year}"
        if year_selector_name in form_data:
            form_data[year_selector_name] = dl_file
            print(f"  → Setting {year_selector_name} to {dl_file}")
        else:
            print(f"  → Year {year} has no dropdown (defaults to English)")
        
        # Submit POST request to problems.aspx
        download_url = f"{base_url}problems.aspx"
        response = session.post(download_url, data=form_data, timeout=30)
        
        # Check if we got a PDF back
        content_type = response.headers.get('content-type', '')
        content_length = len(response.content)
        
        # A real PDF should be larger than 75KB and have the right content type
        if content_length > 100000 or 'application/pdf' in content_type:
            # Additional check: PDFs start with %PDF
            if response.content.startswith(b'%PDF'):
                filename = f"IMO_{year}_Problems_English.pdf"
                filepath = os.path.join(download_folder, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                print(f"✓ Successfully downloaded: {filename} ({content_length} bytes)")
                return True
            else:
                print(f"✗ Response for year {year} is not a valid PDF")
                return False
        else:
            print(f"✗ Could not download problems for year {year} (response size: {content_length} bytes)")
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
    
    # Extract all language selectors and their default values
    print("Extracting form data from page...")
    language_selectors = extract_language_selectors(soup)
    print(f"Found {len(language_selectors)} language selectors\n")
    
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
            if download_problem_pdf(session, year, language_selectors, base_url, download_folder):
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