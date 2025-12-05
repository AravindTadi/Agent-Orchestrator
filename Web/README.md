# Interactive AI Agent Hub 🤖✨

A modern, interactive web application featuring two distinct AI personalities powered by **Llama 3.3 (70B)** via the Groq API.

## 🌟 Features

*   **Dual Personalities**:
    *   **Nova**: A logical, futuristic assistant focused on science and technology.
    *   **Blaze**: A creative, rebellious spirit who loves art and poetry.
*   **Modern UI**: sleek dark mode design with glassmorphism effects and smooth animations.
*   **Fast Response**: Powered by Groq's LPU inference engine for near-instant AI replies.
*   **Tech Stack**: Python (FastAPI) backend + Vanilla HTML/CSS/JS frontend.

## 🚀 Getting Started

### Prerequisites
*   Python 3.8+
*   A free API key from [Groq Console](https://console.groq.com/keys)

### Installation

1.  **Clone the repository** (or download the files).

2.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn python-multipart groq python-dotenv
    ```

3.  **Setup API Key**:
    *   Create a `.env` file in the `Agents` folder (one level up from `Web`).
    *   Add your key:
        ```text
        GROQ_API_KEY=gsk_your_key_here
        ```

### Running the App

1.  **Start the Backend**:
    Navigate to the `Web` folder and run:
    ```bash
    python3 backend.py
    ```
    The server will start at `http://localhost:8000`.

2.  **Launch the Frontend**:
    Simply open `index.html` in your web browser.

3.  **Chat!**:
    Click "Connect" on either agent to start a conversation.

## 📂 Project Structure

*   `backend.py`: FastAPI server handling chat requests and prompt engineering.
*   `index.html`: Main user interface.
*   `style.css`: Styling and animations.
*   `script.js`: Frontend logic for chat interaction.
