**A Full-Stack Web Application for Data Handling**





AFSWADH is a dynamic, full-stack web application designed to streamline two common data-handling tasks: web scraping and file format conversion. Built with Python (Flask) on the backend and a modern HTML, CSS, and JavaScript front end, this tool provides a powerful and intuitive user experience.



The application's core feature is a multi-threaded web scraper that can extract various types of content from any URL, including links, images, and text. This process runs asynchronously, ensuring the user interface remains responsive with a live progress bar.



Additionally, AFSWADH serves as a robust file converter. Users can upload a CSV file and convert it into popular formats such as Excel, JSON, PDF, and HTML tables.



Key Features

Asynchronous Web Scraping: Uses multi-threading to scrape web content from a given URL without blocking the user interface.



Real-Time Progress: A live progress bar provides instant feedback during long-running scraping jobs.



Secure File Handling: Implements best practices for secure file handling, including filename sanitization and in-memory storage with thread locks.



Versatile File Conversion: Supports converting CSV files to multiple formats including XLSX, JSON, PDF, and HTML.



Clean and Responsive UI: A modern, user-friendly interface that is fully responsive and accessible on both desktop and mobile devices.



How to Set Up and Run the Local Prototype

1\. Prerequisites

Before you begin, ensure you have Python 3.x and pip installed on your machine.



2\. Install Dependencies

Install all the required Python libraries by running the following command in your terminal. This will ensure all the necessary components for the Flask application are available.



pip install Flask requests beautifulsoup4 pandas openpyxl reportlab



3\. Run the Application

Start the Flask development server by running the following commands in your terminal from the project's directory:



For macOS/Linux:



export FLASK\_APP=CSV\_to\_anything.py

flask run



For Windows:



set FLASK\_APP=CSV\_to\_anything.py

flask run



4\. Access the Application

Once the server is running, you can access the application by opening your web browser and navigating to:



https://www.google.com/search?q=http://127.0.0.1:5000



Enjoy using the prototype!

