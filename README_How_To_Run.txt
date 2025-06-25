
✅ HOW TO RUN LOCALLY (STEP-BY-STEP)

1. Make sure Python is installed: https://www.python.org/downloads/

2. Unzip this folder and open a terminal or command prompt inside the folder

3. Install required libraries:
   pip install -r requirements.txt

4. Run the app:
   streamlit run matcher_app.py

5. A browser window will open with your app:
   - Upload your Client and Phone List CSV
   - Upload your Call Log CSV
   - The app will:
     ✅ Match numbers using longest call
     ✅ Flag duplicates
     ✅ Add Vendor info when appropriate
     ✅ Flag missing numbers with "NEED TO CHECK"
     ✅ Generate the Queue Stats section at the end
   - Click to download the final result

To host online instead, follow the GitHub + Streamlit Cloud guide.
