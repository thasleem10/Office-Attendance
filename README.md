# Employee Face Recognition Attendance System

A web-based attendance management system using Python, Flask, OpenCV, and the `face_recognition` (dlib) library. Employees are identified via photo upload, and their check-in/check-out times are automatically logged locally and to Google Sheets.

## Features
- **Face Recognition**: Powered by dlib's state-of-the-art model.
- **Attendance Rules**: First scan = Check-In. Second scan = Check-Out.
- **Dual Storage**: Logs to a local CSV by default, and seamlessly syncs to Google Sheets if configured.
- **Model Training**: Upload a ZIP file of employee photos directly via the web UI to train/retrain the model at runtime.
- **Modern UI**: Glassmorphism design, dark mode, responsive upload handling.

## 1. Setup Instructions

### Prerequisites (Important for Windows)
The core library, `face_recognition`, relies on `dlib`, which usually requires C++ build tools on Windows.

**If you get a "Failed building wheel for dlib" error**, it means you don't have Visual Studio C++ tools installed. The easiest fix for **Python 3.12** on Windows is to install a pre-compiled `.whl` file instead of building from source:

1. Download the pre-built dlib wheel for Python 3.12 from here:
   [dlib-19.24.2-cp312-cp312-win_amd64.whl](https://github.com/z-mahmud22/Dlib_Windows_Python3.x/blob/main/dlib-19.24.2-cp312-cp312-win_amd64.whl) 
   *(Click "Download Raw File")*
2. Save it to your project folder.
3. Install it directly using pip:
   ```bash
   pip install dlib-19.24.2-cp312-cp312-win_amd64.whl
   ```
4. Once dlib is installed successfully, you can install the rest of the file:
   ```bash
   pip install face_recognition Flask gspread google-auth numpy opencv-python-headless Pillow python-dotenv werkzeug
   ```

*Alternative (The Hard Way)*: Install Visual Studio Build Tools (Desktop development with C++), install CMake (`pip install cmake`), and then run `pip install -r requirements.txt`.

### Configuration
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` with your secure keys.

## 2. Google Sheets API Integration (Optional)
If you want attendance pushed to Google Sheets automatically:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a Project and enable the **Google Sheets API** and **Google Drive API**.
3. Create a **Service Account** and download its JSON key file.
4. Rename that file to `credentials.json` and place it in the root of this project.
5. Create a new Google Sheet.
6. **Important**: Share your Google Sheet (give Editor access) to the `client_email` address found inside your `credentials.json` file.
7. Copy the Sheet ID from the URL (the long string between `/d/` and `/edit`).
8. Add the ID to your `.env` file under `GOOGLE_SHEET_ID=`

*If you skip this step, the app will log attendance locally to `data/attendance.csv` without throwing errors.*

## 3. Running the Application
1. Start the Flask server:
   ```bash
   python app.py
   ```
2. Open `http://127.0.0.1:5000` in your web browser.

## 4. How to Use
1. **Train the Model**: Navigate to "Train Model" in the navigation bar.
2. Upload a ZIP file containing employee folders (e.g., `dataset.zip` contains folder `Alice_Smith/` which contains photos of Alice).
3. **Log Attendance**: Go to the homepage and drag-and-drop an employee's photo.
4. **View Logs**: See the "Logs" page for a table of all recorded attendance.
