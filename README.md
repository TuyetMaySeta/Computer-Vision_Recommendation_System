# Set up venv
python -m venv venv

venv\Scripts\activate

 # 1. Setup REQUIREMENT
pip install -r requirements.txt

# 2. Initialize database
python scripts/init_db.py

# 3. Collect videos (chọn một trong hai)
python scripts/collect_by_keyword.py
# hoặc
python scripts/collect_by_channel.py
conda activate youtube-search


# 4. Build embeddings
python scripts/build_embeddings.py

# 5. Search!
# Text only
python scripts/search_videos.py -q "machine learning tutorial" -o results.json

# Text + File
python scripts/search_videos.py  -q "video for preparing interview from file pdf" -f "C:\Users\ADMIN\Downloads\[JD_D&A]- Junior Data Scientist_ver4.0.pdf" -o results.json

#  File
python scripts/search_videos.py -f “C:/paper.pdf” -o results.json
# Text+Image
python scripts/search_videos.py  -q "video for preparing interview from file pdf" -i "link image" -o results.json




