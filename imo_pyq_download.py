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

def get_english_pdf_url(year_url, base_url):
    """
    For pre-2006 years, fetch the year page and find the English PDF download link
    """
    try:
        response = requests.get(year_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for download links - typically in a form or direct link
        # The actual structure may vary, so we'll look for PDF links
        pdf_links = soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())
        
        if pdf_links:
            # Return the first PDF link found (usually the English version)
            pdf_url = pdf_links[0].get('href')
            return urljoin(base_url, pdf_url)
        
        return None
    except Exception as e:
        print(f"Error fetching year page: {str(e)}")
        return None

def main():
    # Setup
    base_url = "https://www.imo-official.org/"
    problems_url = "https://www.imo-official.org/problems.aspx"
    download_folder = str(Path.home() / "Downloads")
    
    print(f"Downloading IMO PDFs to: {download_folder}\n")
    
    # Fetch the main problems page
    try:
        response = requests.get(problems_url, timeout=30)
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
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        
        # Extract year
        year_link = cells[0].find('a')
        if not year_link:
            continue
        
        year = year_link.text.strip()
        year_url = urljoin(base_url, year_link.get('href'))
        
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
        
        # Check for English version (column 2, for older years)
        english_cell = cells[1]
        english_link = english_cell.find('a', string='English')
        
        if english_link:
            # For pre-2006 years, we need to visit the year page
            # and find the actual PDF download link
            print(f"Fetching English PDF for year {year}...")
            
            pdf_url = get_english_pdf_url(year_url, base_url)
            
            if pdf_url:
                filename = f"IMO_{year}_Problems_English.pdf"
                if download_pdf(pdf_url, filename, download_folder):
                    downloaded += 1
                else:
                    failed += 1
            else:
                print(f"✗ Could not find PDF link for year {year}")
                failed += 1
            
            time.sleep(1)  # Be polite to the server
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Download Summary:")
    print(f"Successfully downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
