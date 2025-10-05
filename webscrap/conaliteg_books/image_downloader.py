import os
import re
import requests
from tqdm import tqdm

# 🔧 Configuration
YEAR = "2025"
BOOK_LIST = """
T0LPM.htm
T1ETA.htm
T1HPA.htm
T1HUA.htm
T1INA.htm
T1LEA.htm
T1LP1.htm
T1LP2.htm
T1LP3.htm
T1MLA.htm
T1SAA.htm
T2ETA.htm
T2HUA.htm
T2INA.htm
T2LEA.htm
T2LP1.htm
T2LP2.htm
T2LP3.htm
T2MLA.htm
T2SAA.htm
T3ETA.htm
T3HUA.htm
T3INA.htm
T3LEA.htm
T3LP1.htm
T3LP2.htm
T3LP3.htm
T3MLA.htm
T3SAA.htm
S0LPM.htm
S1ETA.htm
S1HPA.htm
S1HUA.htm
S1INA.htm
S1LEA.htm
S1MLA.htm
S1NLA.htm
S1SAA.htm
S2ETA.htm
S2HUA.htm
S2INA.htm
S2LEA.htm
S2MLA.htm
S2NLA.htm
S2SAA.htm
S3ETA.htm
S3HUA.htm
S3INA.htm
S3LEA.htm
S3MLA.htm
S3NLA.htm
S3SAA.htm
P1LPM.htm
P1MLA.htm
P1PAA.htm
P1PCA.htm
P1PEA.htm
P1SDA.htm
P1TNA.htm
P1TPA.htm
P2MLA.htm
P2PAA.htm
P2PCA.htm
P2PEA.htm
P2SDA.htm
P2TNA.htm
P2TPA.htm
P3LPM.htm
P3MLA.htm
P3PAA.htm
P3PCA.htm
P3PEA.htm
P3SDA.htm
P0CMA.htm
P0SHA.htm
P4MLA.htm
P4PAA.htm
P4PCA.htm
P4PEA.htm
P4SDA.htm
P5LPM.htm
P5MLA.htm
P5PAA.htm
P5PCA.htm
P5PEA.htm
P5SDA.htm
P6MLA.htm
P6PAA.htm
P6PCA.htm
P6PEA.htm
P6SDA.htm
K0CFA.htm
K0LPM.htm
K0MTM.htm
K0TAM.htm
K1LDG.htm
K1LMA.htm
K1LPA.htm
K1MLA.htm
K2LDG.htm
K2LMA.htm
K2LPA.htm
K2MLA.htm
K3LDG.htm
K3LMA.htm
K3LPA.htm
K3MLA.htm
""".strip().splitlines()

# Clean list: remove empty lines and duplicates
BOOK_CODES = list(dict.fromkeys([
    line.strip().replace('.htm', '')
    for line in BOOK_LIST
    if line.strip()
]))

BASE_URL = f"https://libros.conaliteg.gob.mx/{YEAR}/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
}

def get_total_pages(book_code):
    """Fetch ag_pages from the .htm page"""
    url = f"{BASE_URL}{book_code}.htm"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'ag_pages\s*=\s*(\d+)', response.text)
        return int(match.group(1)) if match else 0
    except Exception as e:
        print(f"❌ Failed to get page count for {book_code}: {e}")
        return 0

def download_book(book_code, total_pages):
    """Download all pages for one book"""
    folder = os.path.join("conaliteg_books", YEAR, book_code)
    os.makedirs(folder, exist_ok=True)
    
    image_base = f"https://libros.conaliteg.gob.mx/{YEAR}/c/{book_code}/"
    
    for i in tqdm(range(1, total_pages + 1), desc=f"{book_code}"):
        page_file = f"{i:03}.jpg"
        img_url = f"{image_base}{page_file}"
        path = os.path.join(folder, page_file)
        
        if os.path.exists(path):
            continue  # skip if already downloaded
        
        try:
            r = requests.get(img_url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                with open(path, "wb") as f:
                    f.write(r.content)
            else:
                tqdm.write(f"⚠️ {book_code} page {i} → HTTP {r.status_code}")
        except Exception as e:
            tqdm.write(f"❌ Error on {book_code} page {i}: {e}")

# 🚀 Main execution
if __name__ == "__main__":
    print(f"📚 Found {len(BOOK_CODES)} unique books to download (Year: {YEAR})")
    
    for book_code in BOOK_CODES:
        print(f"\n🔍 Processing: {book_code}")
        total = get_total_pages(book_code)
        if total > 0:
            print(f"   → Total pages: {total}")
            download_book(book_code, total)
        else:
            print(f"   → ❌ Skipped (no page count)")
    
    print(f"\n🎉 All done! Books saved in 'conaliteg_books/{YEAR}/'")