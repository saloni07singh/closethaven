# ClosetHaven | Personal Closet Intelligence

**Wear more of what you own.**

ClosetHaven is an agentic personal closet intelligence platform developed to help people organise their existing clothing, discover outfit combinations, plan what to wear and make better use of what they already own.

The project addresses a common problem: people often own plenty of clothes but struggle to remember what they have, find suitable combinations or keep track of which items are available.

ClosetHaven brings digital closet management, AI-assisted features, outfit recommendations and wear tracking into one platform, with a focus on sustainable clothing utilisation.

---

## Project Overview

ClosetHaven was developed as a working web application for the **Agentic AI Hackathon 2026**, under the theme:

**Agentic AI for Climate, Sustainability and Green Innovation**

- **Team:** T063 | Tech Titans
- **Team Members:** Saloni Singh and Aaron Mendonca
- **Primary Focus:** Sustainable clothing utilisation
- **Project Type:** Working MVP / Web Application

## Key Features

### 1. Digital Closet Management

Organise and manage clothing through a digital closet.

- Add clothing using images uploaded from a device or captured through a supported camera.
- Organise clothing into categories.
- Review and edit clothing details.
- Use AI-assisted image recognition to suggest clothing details when the Gemini service is available.
- Track whether clothing is available or currently in the laundry.
- View saved clothing through an organised interface.

### 2. AI-Assisted Styling

Generate outfit suggestions using clothing already recorded in the user's digital closet.

- Explore outfit combinations for different occasions.
- Use available clothing as the basis for recommendations.
- Review suggested combinations before selecting an outfit.
- Reduce the effort involved in deciding what to wear.

### 3. Rewear Rescue

**Rewear Rescue is ClosetHaven's main showstopper.**

It helps users rediscover and reuse their existing clothing through an occasion-based outfit recommendation workflow.

The workflow:

1. The user describes an occasion and their outfit requirements.
2. The system retrieves relevant items from the recorded digital closet.
3. Items marked unavailable or in the laundry are excluded.
4. Suitable outfit combinations are generated using the available inventory.
5. The user reviews the recommendations and chooses a preferred combination.
6. The selected outfit can be saved or scheduled.
7. Wear history can be updated after the user confirms that the outfit was actually worn.

This connected workflow is called the **Rewear Intelligence Loop**.

The user retains control over the final outfit selection and confirmation of actual wear.

### 4. Outfit Planning and Wear Tracking

- Save preferred outfit combinations.
- Schedule outfits for upcoming occasions.
- View planned outfits.
- Confirm when a scheduled outfit has actually been worn.
- Maintain wear history based on user confirmation.
- View wardrobe usage indicators.

A scheduled outfit is not automatically recorded as worn. Actual wear history changes only after user confirmation.

---

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| AI Integration | Google Gemini API |
| Image Processing | Pillow |
| Web Server | Gunicorn |
| Deployment | Render |

### System Architecture

The application follows a web-based client-server architecture.

1. **Frontend:** HTML, CSS and JavaScript provide the user interface and interactive features.
2. **Backend:** Flask handles application routes, requests, feature logic and communication between components.
3. **Database:** SQLite stores closet information and application data.
4. **AI Integration:** The Gemini API supports optional AI-assisted functionality, including image recognition when configured and available.
5. **Image Processing:** Pillow handles image resizing and compression.
6. **Deployment:** Gunicorn serves the Flask application on Render.

---

## Project Structure

The main project components include:

- `app.py` - Flask application and backend logic.
- `templates/` - HTML templates.
- `static/` - CSS, JavaScript and static assets.
- `requirements.txt` - Python dependencies.
- `Procfile` - Application start configuration.
- `render.yaml` - Render deployment configuration.
- `.gitignore` - Files and folders excluded from Git tracking.

---

## Running the Project Locally

### Prerequisites

- Python 3.11 or a compatible Python version.
- Visual Studio Code or another code editor.
- Git.
- A Gemini API key for optional AI-assisted functionality.

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/saloni07singh/closethaven.git
```

**2. Open the project directory**

```bash
cd closethaven
```

**3. Create a virtual environment**

On Windows:

```powershell
py -3.11 -m venv .venv
```

**4. Activate the virtual environment**

```powershell
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

**5. Install dependencies**

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**6. Configure environment variables**

Set the required environment variables in your local terminal. For example, in PowerShell:

```powershell
$env:GEMINI_API_KEY = "your_own_api_key"
$env:FLASK_SECRET_KEY = "your_own_secret_key"
```

Use your own credentials. Never commit actual API keys or secret values to GitHub.

**7. Run the application**

```bash
python app.py
```

**8. Open the application**

Visit:

http://127.0.0.1:5000

---

## Deployment

ClosetHaven is deployed as a Flask web application using **Render**.

The repository includes a `Procfile` and Render configuration to support deployment.

The deployed application uses environment variables for sensitive configuration, including the Gemini API key and Flask secret key.

API credentials should be configured through the hosting provider's environment settings and must never be hardcoded into application source files or exposed through frontend code.

---

## Important Limitations

ClosetHaven is a hackathon MVP and is not yet a production-ready multi-user SaaS platform.

- Clothing availability and laundry status depend on user updates.
- The application uses a shared closet data model rather than separate authenticated accounts for multiple users.
- Rewear Rescue uses application-side outfit-generation logic to retrieve and recommend combinations from recorded inventory.
- Gemini-assisted functionality depends on API availability, configuration and usage limits.
- The application uses SQLite and local image storage. On hosting environments without persistent storage, data may be lost following restarts or redeployments.
- The application does not currently provide fully automated laundry detection or external calendar synchronisation.
- A production release would require individual user authentication, per-user data isolation, persistent managed storage, backups, stronger security controls and further testing.

---

## Sustainability Focus

ClosetHaven encourages users to make better use of clothing they already own.

By helping users rediscover underused items, explore new combinations and track actual wear, the platform aims to support more thoughtful clothing utilisation.

Potential future evaluation metrics include:

- Increased wear frequency of underused clothing.
- Number of previously unused items rediscovered.
- Number of outfit combinations created from existing inventory.
- Purchases users report avoiding because they reused existing clothing.

These are proposed indicators for future evaluation, not measured environmental outcomes.

---

## Future Scope

Potential areas for further development include:

- Improved clothing recognition and image processing.
- Personalised recommendations based on user preferences and wear history.
- More advanced outfit-planning capabilities.
- Individual user accounts and secure personal closet storage.
- Persistent database and cloud image storage.
- Improved sustainability insights.
- Integrations with clothing repair, resale, donation and recycling services.

---

## Hackathon Participation

ClosetHaven was developed by **Team T063 | Tech Titans** for the Agentic AI Hackathon 2026.

The project explored how agentic workflows and personal closet intelligence could encourage sustainable clothing utilisation through a practical working MVP.

The hackathon provided an opportunity to develop the concept, build the application, deploy it and present the solution to the judging panel.

### Team

- **Saloni Singh**
- **Aaron Mendonca** - Team Leader

---

## Project

**ClosetHaven | Personal Closet Intelligence**

*Helping people make better use of what they already own.*

**Developed by Team T063 | Tech Titans**