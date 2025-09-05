# This is a full-featured web application that can scrape links from a URL
# or convert an uploaded CSV file into various formats.
#
# To run this script, you will need to install the following libraries:
# pip install Flask requests beautifulsoup4 pandas openpyxl reportlab
#
# To launch the application, follow these steps in your terminal:
# 1. set FLASK_APP=Data_Grab.py (Windows) OR export FLASK_APP=Data_Grab.py (macOS/Linux)
# 2. flask run

from flask import Flask, render_template_string, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import io
import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
import json
from urllib.parse import urlparse, urljoin
import uuid
import threading
import time
from collections import deque
import os
import re

app = Flask(__name__)

# A simple in-memory store to hold generated files and task status.
# This simulates a background task and is a good first step towards
# a more robust, asynchronous architecture.
task_status = {}
file_store = {}

# A simple lock for thread-safe access to file_store.
file_store_lock = threading.Lock()

# The HTML for the user interface, including two distinct forms for
# scraping and file conversion.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Scraper & File Converter</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #1a202c; /* Dark background */
            color: #e2e8f0; /* Light text */
        }
        .main-container {
            display: flex;
            flex-direction: column;
            gap: 2rem;
            width: 100%;
            max-width: 800px;
        }
        .card {
            background-color: #2d3748; /* Darker card background */
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            padding: 2.5rem;
            width: 100%;
            text-align: center;
        }
        h1 {
            color: #a0aec0;
            margin-bottom: 1.5rem;
            font-size: 2.5rem;
            font-weight: 700;
        }
        h2 {
            color: #e2e8f0;
            margin-top: 0;
            font-size: 1.75rem;
            font-weight: 600;
        }
        p {
            color: #a0aec0;
            margin-bottom: 2rem;
            line-height: 1.6;
        }
        input, select, button {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #4a5568;
            border-radius: 8px;
            box-sizing: border-box;
            font-size: 1rem;
            background-color: #4a5568;
            color: #e2e8f0;
            transition: all 0.3s ease;
        }
        input::placeholder {
            color: #a0aec0;
        }
        input:focus, select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 5px rgba(102, 126, 234, 0.5);
        }
        button {
            background-image: linear-gradient(to right, #4c51bf, #667eea);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(76, 81, 191, 0.4);
        }
        button:disabled {
            background-image: none;
            background-color: #4a5568;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        .status {
            margin-top: 1.5rem;
            min-height: 20px;
        }
        .status.loading {
            color: #667eea;
            font-weight: 500;
        }
        .status.success {
            color: #48bb78;
            font-weight: bold;
        }
        .status.error {
            color: #fc8181;
            font-weight: bold;
        }
        .loader-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        .loader {
            border: 4px solid #4a5568;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .progress-bar-container {
            width: 100%;
            background-color: #4a5568;
            border-radius: 8px;
            margin-top: 1rem;
            overflow: hidden;
        }
        .progress-bar {
            height: 15px;
            width: 0%;
            background-image: linear-gradient(to right, #48bb78, #38a169);
            border-radius: 8px;
            transition: width 0.3s ease;
        }
        .file-upload-label {
            display: block;
            background-color: #4a5568;
            color: #e2e8f0;
            padding: 0.75rem;
            border: 1px dashed #718096;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .file-upload-label:hover {
            background-color: #667eea;
        }
        #file-input {
            display: none;
        }
        /* Message Box styles */
        .message-box {
            position: fixed;
            inset: 0;
            background-color: rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            justify-content: center;
        }
        .message-box-content {
            background-color: #2d3748;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 90%;
            max-width: 400px;
            text-align: center;
        }
    </style>
</head>
<body class="flex justify-center items-center min-h-screen p-8">
    <div class="main-container">
        <h1 class="text-center text-4xl font-extrabold text-gray-100 mb-8">DataFlow</h1>

        <div class="card">
            <h2>Web Scraper</h2>
            <p>Enter a URL to scrape all links and download them in your desired format.</p>
            <form id="scraper-form" class="space-y-4">
                <input type="text" id="url-input" placeholder="https://example.com" required>
                <input type="text" id="filter-input" placeholder="Optional: Filter links by a keyword">
                <select id="tag-select">
                    <option value="a">Links (&lt;a&gt;)</option>
                    <option value="img">Images (&lt;img&gt;)</option>
                    <option value="h1,h2,h3,h4,h5,h6">Headings (&lt;h1-h6&gt;)</option>
                    <option value="p">Paragraphs (&lt;p&gt;)</option>
                </select>
                <div>
                    <label for="depth-input" class="block text-sm font-medium text-gray-300 text-left mb-1">Scrape Depth</label>
                    <p class="text-xs text-gray-400 mb-2 text-left">
                        A depth of **0** scrapes only the URL you provide. <br>
                        A depth of **1** scrapes the initial URL and all pages linked from it.<br>
                        A depth of **2** scrapes all pages linked from the depth 1 pages as well.
                    </p>
                    <input type="number" id="depth-input" placeholder="0-2" min="0" max="2" value="0">
                </div>
                <select id="scrape-format-select">
                    <option value="csv">CSV</option>
                    <option value="xlsx">Excel (xlsx)</option>
                    <option value="pdf">PDF</option>
                    <option value="json">JSON</option>
                    <option value="html">HTML Table</option>
                </select>
                <button type="submit" id="scrape-button">Scrape & Download</button>
            </form>
            <div id="scrape-status" class="status"></div>
            <div id="progress-container" class="progress-bar-container" style="display: none;">
                <div id="progress-bar" class="progress-bar"></div>
            </div>
        </div>

        <div class="card">
            <h2>File Converter</h2>
            <p>Upload a CSV file and convert it to your desired format.</p>
            <form id="converter-form" enctype="multipart/form-data" class="space-y-4">
                <input type="file" id="file-input" name="file" accept=".csv" required>
                <label for="file-input" class="file-upload-label">Choose a CSV file...</label>
                <select id="convert-format-select">
                    <option value="xlsx">Excel (xlsx)</option>
                    <option value="pdf">PDF</option>
                    <option value="json">JSON</option>
                    <option value="html">HTML Table</option>
                </select>
                <button type="submit" id="convert-button">Convert & Download</button>
            </form>
            <div id="convert-status" class="status"></div>
        </div>
    </div>

    <!-- Message Box UI -->
    <div id="messageBox" class="message-box">
        <div class="message-box-content">
            <h3 class="text-lg font-bold mb-2">Notice</h3>
            <p id="messageText" class="text-sm text-gray-400 mb-4"></p>
            <button id="closeMessageBox" class="w-full py-2 px-4 rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700">
                OK
            </button>
        </div>
    </div>


    <script>
        const messageBox = document.getElementById('messageBox');
        const messageText = document.getElementById('messageText');
        const closeMessageBox = document.getElementById('closeMessageBox');

        function showMessage(message) {
            messageText.textContent = message;
            messageBox.style.display = 'flex';
        }

        closeMessageBox.addEventListener('click', () => {
            messageBox.style.display = 'none';
        });

        // Set up the form submission for the web scraper
        document.getElementById('scraper-form').addEventListener('submit', function(event) {
            event.preventDefault();

            const url = document.getElementById('url-input').value;
            const tag = document.getElementById('tag-select').value;
            const depth = document.getElementById('depth-input').value;
            const filter_keyword = document.getElementById('filter-input').value;
            const format = document.getElementById('scrape-format-select').value;
            const statusDiv = document.getElementById('scrape-status');
            const submitButton = document.getElementById('scrape-button');
            const progressBarContainer = document.getElementById('progress-container');
            const progressBar = document.getElementById('progress-bar');

            // Show a loading state
            statusDiv.innerHTML = '<div class="loader-container"><div class="loader"></div><div class="progress-info">Starting scrape...</div></div>';
            statusDiv.className = 'status loading';
            submitButton.disabled = true;
            progressBarContainer.style.display = 'block';
            progressBar.style.width = '0%';

            fetch('/start-scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, format: format, tag: tag, filter_keyword: filter_keyword, depth: depth })
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                } else {
                    return response.text().then(text => { throw new Error(text); });
                }
            })
            .then(data => {
                // Polling for the task status
                const taskId = data.task_id;
                const pollInterval = setInterval(() => {
                    fetch('/status/' + taskId)
                        .then(res => res.json())
                        .then(statusData => {
                            if (statusData.status === 'completed') {
                                clearInterval(pollInterval);
                                statusDiv.innerHTML = `
                                    <strong>Scrape complete!</strong><br>
                                    Total Items Found: ${statusData.summary.total_items}
                                `;
                                statusDiv.className = 'status success';

                                // Trigger the download
                                const link = document.createElement('a');
                                link.href = '/download/' + statusData.file_id;
                                link.download = statusData.filename;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                                submitButton.disabled = false;
                                progressBarContainer.style.display = 'none';

                            } else if (statusData.status === 'failed') {
                                clearInterval(pollInterval);
                                showMessage('Error: ' + statusData.error);
                                statusDiv.textContent = '';
                                statusDiv.className = 'status error';
                                submitButton.disabled = false;
                                progressBarContainer.style.display = 'none';
                            } else if (statusData.status === 'in_progress') {
                                // Update progress bar and text
                                const progressPercentage = statusData.progress.percentage;
                                progressBar.style.width = `${progressPercentage}%`;
                                statusDiv.querySelector('.progress-info').textContent = statusData.progress.message;
                            }
                        })
                        .catch(error => {
                            clearInterval(pollInterval);
                            showMessage('Error polling for status: ' + error.message);
                            statusDiv.textContent = '';
                            statusDiv.className = 'status error';
                            submitButton.disabled = false;
                            progressBarContainer.style.display = 'none';
                        });
                }, 1000); // Poll every 1 seconds

            })
            .catch(error => {
                showMessage('Error starting scrape: ' + error.message);
                statusDiv.textContent = '';
                statusDiv.className = 'status error';
                console.error('Operation failed:', error);
                submitButton.disabled = false;
                progressBarContainer.style.display = 'none';
            })
        });

        // Set up the form submission for the file converter
        document.getElementById('converter-form').addEventListener('submit', function(event) {
            event.preventDefault();

            const fileInput = document.getElementById('file-input');
            const file = fileInput.files[0];
            const format = document.getElementById('convert-format-select').value;
            const statusDiv = document.getElementById('convert-status');
            const submitButton = document.getElementById('convert-button');

            if (!file) {
                showMessage('Please select a file to upload.');
                return;
            }

            statusDiv.innerHTML = '<div class="loader-container"><div class="loader"></div><div class="progress-info">Converting... Please wait.</div></div>';
            statusDiv.className = 'status loading';
            submitButton.disabled = true;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('format', format);

            fetch('/convert', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (response.ok) {
                    return response.json();
                } else {
                    return response.text().then(text => { throw new Error(text); });
                }
            })
            .then(data => {
                 statusDiv.textContent = 'Conversion complete! Downloading file.';
                 statusDiv.className = 'status success';

                // Trigger the download
                const link = document.createElement('a');
                link.href = '/download/' + data.file_id;
                link.download = data.filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            })
            .catch(error => {
                showMessage('Error: ' + error.message);
                statusDiv.textContent = '';
                statusDiv.className = 'status error';
                console.error('Operation failed:', error);
            })
            .finally(() => submitButton.disabled = false);
        });

        // Handle file input label
        document.getElementById('file-input').addEventListener('change', function(e) {
            const fileName = e.target.files[0] ? e.target.files[0].name : "Choose a CSV file...";
            document.querySelector('.file-upload-label').textContent = fileName;
        });
    </script>
</body>
</html>
"""


# Function to sanitize filenames to prevent path traversal
def sanitize_filename(filename):
    """
    Sanitizes a filename to prevent directory traversal attacks.
    """
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    return filename


# The main route for the web page
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


# Helper function to convert a pandas DataFrame to the specified format and returns a file object
def create_file_object(df, output_format):
    """
    Converts a pandas DataFrame to the specified format and returns a file-like object.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename_base = f"output_{timestamp}"

    try:
        if output_format == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return {
                "file_obj": io.BytesIO(output.getvalue().encode('utf-8')),
                "mimetype": 'text/csv',
                "filename": f'{filename_base}.csv'
            }

        elif output_format == 'xlsx':
            output = io.BytesIO()
            df.to_excel(output, index=False)
            output.seek(0)
            return {
                "file_obj": output,
                "mimetype": 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                "filename": f'{filename_base}.xlsx'
            }

        elif output_format == 'pdf':
            output = io.BytesIO()
            doc = SimpleDocTemplate(output, pagesize=letter)

            data = [df.columns.tolist()] + df.values.tolist()
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements = [table]
            doc.build(elements)

            output.seek(0)
            return {
                "file_obj": output,
                "mimetype": 'application/pdf',
                "filename": f'{filename_base}.pdf'
            }

        elif output_format == 'json':
            output = io.StringIO()
            df.to_json(output, orient='records', indent=4)
            output.seek(0)
            return {
                "file_obj": io.BytesIO(output.getvalue().encode('utf-8')),
                "mimetype": 'application/json',
                "filename": f'{filename_base}.json'
            }

        elif output_format == 'html':
            html_table = df.to_html(index=False, classes='table-auto', escape=False)
            full_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Converted Table</title>
                <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
                    body {{ font-family: 'Inter', sans-serif; margin: 2rem; background-color: #2d3748; color: #e2e8f0; }}
                    .container {{ background-color: #4a5568; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                    h1 {{ color: #e2e8f0; text-align: center; }}
                    .table-auto {{ width: 100%; border-collapse: collapse; }}
                    .table-auto th, .table-auto td {{ border: 1px solid #718096; padding: 8px; text-align: left; }}
                    .table-auto th {{ background-color: #4a5568; color: #a0aec0; }}
                    .table-auto tr:nth-child(even) {{ background-color: #2d3748; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1 class="text-xl font-bold mb-4">Converted Table</h1>
                    {html_table}
                </div>
            </body>
            </html>
            """
            output = io.StringIO()
            output.write(full_html)
            output.seek(0)
            return {
                "file_obj": io.BytesIO(output.getvalue().encode('utf-8')),
                "mimetype": 'text/html',
                "filename": f'{filename_base}.html'
            }
        else:
            return None
    except Exception as e:
        print(f"Error during file creation: {e}")
        return None


# The task that will run in a separate thread.
def scrape_task(task_id, url, output_format, tag, filter_keyword, depth):
    """
    Performs the web scraping in a background thread using an iterative approach.
    """
    global task_status, file_store, file_store_lock

    # Initialize task status with progress tracking
    task_status[task_id] = {
        "status": "in_progress",
        "progress": {
            "percentage": 0,
            "message": "Initializing...",
            "pages_processed": 0,
            "total_items": 0
        }
    }

    scraped_data = []
    visited_urls = set()
    url_queue = deque([(url, 0)])  # (url, current_depth)

    try:
        while url_queue:
            current_url, current_depth = url_queue.popleft()

            # Avoid re-visiting URLs or exceeding depth limit
            if current_url in visited_urls or current_depth > int(depth):
                continue

            visited_urls.add(current_url)

            # Update progress status
            task_status[task_id]["progress"]["pages_processed"] = len(visited_urls)
            task_status[task_id]["progress"]["message"] = f"Scraping page {len(visited_urls)}..."

            # Estimate progress percentage based on total expected visits (initial URL + new links)
            # Note: This is a simple heuristic and might not be perfectly accurate.
            estimated_total_pages = len(visited_urls) + len(url_queue)
            if estimated_total_pages > 0:
                percentage = int((len(visited_urls) / (estimated_total_pages)) * 100)
                task_status[task_id]["progress"]["percentage"] = percentage
            else:
                task_status[task_id]["progress"]["percentage"] = 0

            try:
                response = requests.get(current_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')

                tags_found = soup.find_all(tag)

                for element in tags_found:
                    text = element.get_text(strip=True)
                    attribute = ''

                    if element.name == 'a' and element.get('href'):
                        attribute = urljoin(current_url, element.get('href'))
                        if attribute.startswith('http') and attribute not in visited_urls:
                            url_queue.append((attribute, current_depth + 1))
                    elif element.name == 'img' and element.get('src'):
                        attribute = urljoin(current_url, element.get('src'))
                    else:
                        attribute = text

                    if filter_keyword and filter_keyword not in (text + ' ' + attribute).lower():
                        continue

                    scraped_data.append({
                        'Source URL': current_url,
                        'Tag': element.name,
                        'Text': text,
                        'Attribute': attribute
                    })

            except requests.exceptions.HTTPError as e:
                scraped_data.append({
                    'Source URL': current_url,
                    'Tag': 'Error',
                    'Text': f'HTTP Error: {e.response.status_code}',
                    'Attribute': f'Could not access URL. Check URL or network.'
                })
            except requests.exceptions.RequestException as e:
                scraped_data.append({
                    'Source URL': current_url,
                    'Tag': 'Error',
                    'Text': f'Connection Error',
                    'Attribute': str(e)
                })
            except Exception as e:
                scraped_data.append({
                    'Source URL': current_url,
                    'Tag': 'Error',
                    'Text': 'Unexpected Error',
                    'Attribute': str(e)
                })

            task_status[task_id]["progress"]["total_items"] = len(scraped_data)

        if not scraped_data:
            task_status[task_id] = {"status": "failed", "error": "No data found or scraping failed."}
            return

        df = pd.DataFrame(scraped_data)

        file_info = create_file_object(df, output_format)
        if file_info is None:
            task_status[task_id] = {"status": "failed", "error": "Failed to create file."}
            return

        file_id = str(uuid.uuid4())
        with file_store_lock:
            file_store[file_id] = file_info

        task_status[task_id] = {
            "status": "completed",
            "file_id": file_id,
            "filename": file_info['filename'],
            "summary": {
                "total_items": len(scraped_data)
            }
        }

    except Exception as e:
        task_status[task_id] = {"status": "failed", "error": f"An unexpected error occurred: {e}"}


# The API endpoint for scraping links from a URL. It now starts a background task.
@app.route('/start-scrape', methods=['POST'])
def start_scrape():
    data = request.json
    url = data.get('url')
    output_format = data.get('format')
    tag = data.get('tag', 'a').split(',')
    filter_keyword = data.get('filter_keyword', '')
    depth = data.get('depth', '0')

    if not url:
        return "URL is required.", 400

    if not output_format:
        return "Output format is required.", 400

    task_id = str(uuid.uuid4())
    thread = threading.Thread(target=scrape_task, args=(task_id, url, output_format, tag, filter_keyword, depth))
    thread.start()

    return jsonify({"status": "processing", "task_id": task_id}), 202  # 202 Accepted status


# The API endpoint for converting an uploaded CSV file
@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return "No file part in the request.", 400

    file = request.files['file']
    output_format = request.form.get('format')

    if file.filename == '':
        return "No selected file.", 400

    if file and file.filename.endswith('.csv'):
        try:
            df = pd.read_csv(io.StringIO(file.stream.read().decode("utf-8")))
            file_info = create_file_object(df, output_format)
            if file_info is None:
                return "Failed to create file.", 500

            file_id = str(uuid.uuid4())
            with file_store_lock:
                file_store[file_id] = file_info

            return jsonify({
                "status": "success",
                "file_id": file_id,
                "filename": file_info['filename']
            })
        except Exception as e:
            return f"Error processing the CSV file: {e}", 400
    else:
        return "File is not a valid CSV.", 400


# New API endpoint to check the status of a long-running task
@app.route('/status/<task_id>', methods=['GET'])
def get_status(task_id):
    if task_id not in task_status:
        return jsonify({"status": "not_found"}), 404

    return jsonify(task_status[task_id])


# New API endpoint to serve the generated file
@app.route('/download/<file_id>', methods=['GET'])
def download_file(file_id):
    with file_store_lock:
        file_info = file_store.get(file_id)

    if not file_info:
        return "File not found.", 404

    # Sanitize the filename to prevent directory traversal
    filename = sanitize_filename(file_info['filename'])

    # Create a shallow copy of the BytesIO/StringIO object to prevent closing the original
    if isinstance(file_info['file_obj'], io.BytesIO):
        file_info['file_obj'].seek(0)
        data_stream = io.BytesIO(file_info['file_obj'].read())
    else:
        file_info['file_obj'].seek(0)
        data_stream = io.StringIO(file_info['file_obj'].read())

    return send_file(
        data_stream,
        mimetype=file_info['mimetype'],
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    app.run(debug=True)
