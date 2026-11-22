# 🎬 Cheat Clip PRO

> **AI Powered Auto Clipper — Turn long YouTube, Google Drive, and uploaded videos into viral TikToks, Shorts, and Reels with animated subtitles, face centering, and music in minutes.**

---

## ⚡ Quick Start & Setup

Follow these steps to set up and run Cheat Clip PRO locally on **Windows**, **macOS**, or **Linux**.

### Step 1: Prerequisites

Make sure you have the following installed:

1. **[Git](https://git-scm.com/)**
   * **Windows:** `winget install Git.Git` or download from [git-scm.com](https://git-scm.com/)
   * **macOS:** `brew install git`
   * **Linux:** `sudo apt install git`
2. **[Node.js](https://nodejs.org/)** (v22 LTS recommended)
   * Download from [nodejs.org](https://nodejs.org/) or install via your package manager.
3. **[Python](https://www.python.org/)** (v3.10 – v3.12 recommended; **Python < 3.13 required**)
   * ⚠️ **Important:** Dependencies like **PyTorch**, **OpenCV**, and **Whisper** do **not** support Python 3.13, 3.14, or 3.15+ yet. You must use **Python 3.10, 3.11 (recommended), or 3.12**.
   * **Windows:** Download Python 3.11 from [python.org](https://www.python.org/downloads/release/python-3119/) (ensure you check *"Add Python to PATH"* during setup).
   * **macOS:** `brew install python@3.11`
   * **Linux:** `sudo apt install python3.11 python3.11-venv python3-pip`
4. **FFmpeg & yt-dlp** (Required to download, slice, and render clips)
   * **Windows (PowerShell):**
     ```powershell
     winget install Gyan.FFmpeg
     winget install yt-dlp.yt-dlp
     ```
     *(Close and reopen your terminal after installing so Windows recognizes them)*
   * **macOS (Terminal):**
     ```bash
     brew install ffmpeg-full yt-dlp
     ```
      `ffmpeg-full` is required for the libass subtitle filter used by rendered captions.
   * **Linux:**
     ```bash
     sudo apt update && sudo apt install ffmpeg
     pip install yt-dlp
     ```

---

### Step 2: Clone the Repository

Open your terminal and clone the repository:

```bash
git clone https://github.com/teamsapasih-cmd/cheat-clip-pro.git
cd cheat-clip-pro
```

---

### Step 3: Install Dependencies

#### 1. Frontend Dependencies
```bash
npm install
```

#### 2. Backend Dependencies
We recommend setting up a Python virtual environment:

* **Windows:**
  ```powershell
  python -m venv venv
  venv\Scripts\activate
  pip install -r backend/requirements.txt
  ```

* **macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -r backend/requirements.txt
  ```

---

### Step 4: Run the App

Launch both the frontend and backend servers concurrently:

```bash
npm run dev
```

* **Web App:** [`http://localhost:5173`](http://localhost:5173)
* **Backend API:** [`http://localhost:8000`](http://localhost:8000)
* **API Documentation:** [`http://localhost:8000/docs`](http://localhost:8000/docs)

---

## 🔄 Updating to the Latest Version

To update Cheat Clip PRO to the latest release:

```bash
git pull
npm install
pip install -r backend/requirements.txt
```
*(Make sure your virtual environment is activated if you created one)*

---

## 🔑 Optional AI configuration

The local editor and rendering tools run on your computer; no hosting account is required.

AI video analysis uses a server-side provider key. To enable it locally:

1. Copy `local.env.example` to `.env` in the repository root.
2. Add your own `GEMINI_API_KEY` to that local `.env` file.
3. Keep the key out of source files, screenshots, Git commits, and browser code.
4. Restart the backend after changing environment variables.

Without an AI key, the application can still be opened and the local interface/editor explored, but AI analysis will not run. AI analysis requires an internet connection and a configured provider.

The Cloud Workspace is a separate cloud feature. It requires PostgreSQL, Redis, and private S3-compatible object storage; it is not needed to develop or use the local editor.

---

## 🎯 How to Use

1. **Paste a YouTube URL** — Enter any podcast, stream, or video link.
2. **Choose Duration** — Pick `~15s` (fast hooks), `~30s` (standard shorts), or `~60s` (story clips).
3. **Click "Analyze Video"** — The AI finds the most exciting moments using YouTube audience retention data.
4. **Customize in Clip Studio** — Adjust your video style:
   * **Frame & Crop**: Fullscreen 9:16 vertical, square, or split-screen facecam.
   * **Face Tracking**: Automatically keeps the speaker in the center of the frame.
   * **Subtitles**: Choose viral animated karaoke caption styles and fonts.
   * **Branding & Audio**: Add your watermark logo, background music, and hook sound effects.
   * **Hardware Acceleration**: Choose your graphics card (NVIDIA, AMD, Intel) or CPU.
5. **Batch Render & Download** — Click **Batch Render**, then download all your finished videos together in one **.ZIP** file!

---

## ❓ Common Problems & Easy Fixes

### 1. "Failed to render video" or `The system cannot find the file specified`
* **Cause:** `ffmpeg` or `yt-dlp` is missing on your computer.
* **Fix:**
  * **Windows (PowerShell):**
    ```powershell
    winget install Gyan.FFmpeg
    winget install yt-dlp.yt-dlp
    ```
    *(Then close and reopen your terminal)*
  * **Mac (Terminal):**
    ```bash
    brew install ffmpeg-full yt-dlp
    ```
  * Or install directly via Python: `pip install yt-dlp`

### 2. `No such filter: 'subtitles'`
* **Cause:** FFmpeg was installed without the libass subtitle filter.
* **Fix (macOS):**
  ```bash
  brew install ffmpeg-full
  ```
  Restart the backend after installation. The app automatically prefers Homebrew's subtitle-capable `ffmpeg-full` binary.

### 3. A video URL cannot be retrieved
* **Cause:** A video platform may restrict automated access or require permissions that the application does not have.
* **Fix:** Use the application's local upload option with a video you own or have permission to process. Do not attempt to bypass platform access controls.

### 4. Does this work on AMD graphics cards and Mac?
* **Yes!** Cheat Clip PRO automatically supports:
  * **NVIDIA** (`h264_nvenc`)
  * **AMD** (`h264_amf` on Radeon GPUs & Ryzen CPUs)
  * **Intel** (`h264_qsv` on Arc & UHD Graphics)
  * **Apple Mac & CPU Software** (`libx264` universal high-speed fallback)
* You can switch your preferred hardware acceleration encoder anytime in the Render Settings or History card.

### 5. `pip install` fails with build errors on PyTorch or OpenCV
* **Cause:** You are running an unsupported version of Python (such as Python 3.13, 3.14, or 3.15+). PyTorch and OpenCV wheels are not yet distributed for these versions.
* **Fix:** Install **Python 3.11** or **3.12**, recreate your virtual environment (`python3.11 -m venv venv`), and run `pip install -r backend/requirements.txt`.

---

## 📄 License & Attribution

Distributed under the **MIT License**. Free for personal and commercial use.

Any copies, forks, or substantial portions of this software must retain the original copyright notice and permission notice found in the LICENSE file.
