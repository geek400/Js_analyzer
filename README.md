# JavaScript Security Analyzer with Gemini AI

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

A powerful tool for analyzing JavaScript files/URLs using Google's Gemini AI to detect security risks, hardcoded secrets, and suspicious patterns.

## Features

- **AI-Powered Analysis**: Uses Gemini 2.5 Flash model to explain JavaScript code
- **Multi-Source Input**: Works with both local files and remote URLs
- **Security Scanning**: Detects:
  - Hardcoded API keys and secrets
  - Suspicious code patterns (eval, unsafe setTimeout)
  - Potential security vulnerabilities
- **Information Extraction**: Automatically extracts:
  - All URLs found in the code
  - Potential tokens/secrets
- **Parallel Processing**: Batch processing with configurable thread count
- **Beautiful Output**: Generates well-formatted Markdown reports

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/js-analyzer.git
   cd js-analyzer
