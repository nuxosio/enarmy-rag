# enarmy-rag

## Installation

### Dependencies

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Milvus Setup

For Milvus installation on Windows, follow the official guide:
https://milvus.io/docs/install_standalone-windows.md

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-api-key
LANGSMITH_PROJECT=default
GOOGLE_API_KEY=your-api-key
```

Note: `GOOGLE_API_KEY` is the Gemini API key.
