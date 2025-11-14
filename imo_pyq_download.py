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
    """
    try:
        # Construct the download URL - this appears to be a form submission
        # We need to POST to the page with the language parameter
        download_url = f"{base_url}problems.aspx"
        
        # Prepare form data to request English version
        form_data = {
            'year': year,
            'language': 'English'
        }
        
        print(f"Fetching English problems for year {year}...")
        
        # Try to submit the form
        response = session.post(download_url, data=form_data, timeout=30)
        
        # Check if we got a PDF back
        if response.headers.get('content-type', '').startswith('application/pdf'):
            filename = f"IMO_{year}_Problems_English.pdf"
            filepath = os.path.join(download_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"✓ Successfully downloaded: {filename}")
            return True
        else:
            # If POST didn't work, try constructing a GET URL
            # The actual URL pattern might be different
            possible_urls = [
                f"{base_url}problems/IMO{year}.pdf",
                f"{base_url}year_info.aspx?year={year}&language=English",
            ]
            
            for url in possible_urls:
                try:
                    response = session.get(url, timeout=30)
                    if response.status_code == 200 and response.headers.get('content-type', '').startswith('application/pdf'):
                        filename = f"IMO_{year}_Problems_English.pdf"
                        filepath = os.path.join(download_folder, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        print(f"✓ Successfully downloaded: {filename}")
                        return True
                except:
                    continue
            
            print(f"✗ Could not download problems for year {year}")
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
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Fetch the main problems page
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
    # We need to reverse engineer how the download button works
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
        
        # Check if there's a language dropdown or English link in column 2
        language_cell = cells[1]
        
        # For now, we'll try to download the English version
        if download_problem_pdf(session, year, base_url, download_folder):
            downloaded += 1
        else:
            failed += 1
        
        time.sleep(1)  # Be polite to the server
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Download Summary:")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()