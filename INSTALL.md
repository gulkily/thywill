# ThyWill Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd thywill
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
cp .env.example .env  # If .env.example exists, or create manually
```

Add your Anthropic API key to the `.env` file:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 5. Initialize Database
The SQLite database will be created automatically when you first run the application.

### 6. Run the Application
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## First Time Setup

1. When you first start the application, it will generate an admin invite token
2. Look for the token in the console output: `==== First-run invite token (admin): <token> ====`
3. Visit `http://localhost:8000/claim/<token>` to create the admin account
4. Use the admin account to generate invite links for other users

## Configuration

- **Session Duration**: Sessions last 14 days by default
- **Invite Token Expiration**: Invite tokens expire after 12 hours
- **Database**: Uses SQLite (`thywill.db`) by default

## Optional Files

- `prompts.yaml` - Daily prompts (format: `YYYY-MM-DD: "prompt text"`)

## Accessing the Application

- Main feed: `http://localhost:8000/`
- Admin panel: `http://localhost:8000/admin` (admin users only)
- Activity feed: `http://localhost:8000/activity`

## Troubleshooting

### Common Issues

1. **Missing Anthropic API Key**: Ensure `ANTHROPIC_API_KEY` is set in your `.env` file
2. **Port Already in Use**: Change the port number in the uvicorn command
3. **Database Errors**: Delete `thywill.db` to reset the database (will lose all data)

### Environment Variables

Required:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for prayer generation

### Development Mode

For development with auto-reload:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment

For production, consider:
- Using a production WSGI server like Gunicorn
- Setting up proper environment variables
- Using a more robust database (PostgreSQL, MySQL)
- Setting up proper logging and monitoring