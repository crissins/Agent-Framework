import os
import img2pdf
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

# 🔧 CORRECTED PATH — relative to current working directory
BASE_DIR = Path("conaliteg_books/2025")  # ← This is the fix
OUTPUT_DIR = Path("output_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)

def create_pdf_for_book(book_folder: Path):
    try:
        image_files = list(book_folder.glob("*.jpg"))
        if not image_files:
            return f"⚠️  No images in {book_folder.name}"
        
        # Sort numerically: 001.jpg, 002.jpg, ..., 259.jpg
        image_files.sort(key=lambda x: int(x.stem))
        
        pdf_path = OUTPUT_DIR / f"{book_folder.name}.pdf"
        
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert([str(img) for img in image_files]))
        
        return f"✅ {book_folder.name} → {len(image_files)} pages"
    
    except Exception as e:
        return f"❌ Failed {book_folder.name}: {e}"

def main():
    if not BASE_DIR.exists():
        raise FileNotFoundError(f"Base directory not found: {BASE_DIR.resolve()}")
    
    book_folders = [f for f in BASE_DIR.iterdir() if f.is_dir()]
    print(f"📦 Found {len(book_folders)} books. Creating PDFs...\n")
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(create_pdf_for_book, folder) for folder in book_folders]
        for future in tqdm(futures, desc="Creating PDFs"):
            print(future.result())

if __name__ == "__main__":
    main()