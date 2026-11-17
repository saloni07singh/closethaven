# ClosetHaven | Tech Titans

Updated hackathon MVP package aligned with the submitted 17-slide presentation.

**Wear more of what you own.**  
ClosetHaven is a personal closet intelligence prototype that helps people organise garments, discover outfit combinations from their existing clothes, plan looks and track confirmed wear.

## What is included

### Digital closet
- Add garments by selecting a photo from your device or taking a photo on a supported mobile browser.
- Photo preview before saving.
- Gemini image recognition can suggest a garment name, category, colour and season when `GEMINI_API_KEY` is configured.
- Garment images are normalized to PNG. Background removal is attempted with `rembg` when its model is available.
- Category and item-type selections, garment cards, availability and laundry status.

### Personal styling and Rewear Rescue
- AI Stylist and Rewear Rescue/Panic Mode generate combinations from actual saved inventory.
- Laundry items are excluded from recommendations.
- Gemini can improve recommendation explanations, but cannot add garments that are absent from the database.
- Live current weather can be retrieved from Open-Meteo when a city is supplied and manual weather context is left blank.
- Users review and approve an outfit before it is saved.

### Planning and wear history
- Save outfits and schedule them for an event/date.
- A scheduled outfit is not automatically counted as worn.
- Wear history changes only after the user explicitly confirms “I wore this”.
- Wardrobe insights report garment and wear activity. They do not claim measured carbon, water or waste savings.

## Technology

- Python + Flask
- HTML, CSS and JavaScript
- SQLite
- Pillow and optional `rembg` background removal
- Google Gemini API for optional image recognition and styling explanations
- Open-Meteo geocoding and weather endpoints
- Gunicorn for hosted deployment

## Run locally on Windows / VS Code

1. Extract the ZIP.
2. Open the `ClosetHaven` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create and activate a virtual environment:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

5. Install dependencies:

   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env`. Add your Gemini key after `GEMINI_API_KEY=`. Keep `.env` private.
7. Start the app:

   ```powershell
   python app.py
   ```

8. Open `http://127.0.0.1:5000`.

If the background-removal model has not downloaded yet, the first image processing request may take longer. If background removal cannot run, the app retains a normalized image rather than blocking garment entry.

## Publish a preview using GitHub + Render

This repository includes a `Procfile` and `render.yaml` for Render.

1. Create a GitHub repository named `closethaven` (or another name you choose).
2. Extract this ZIP and open the `digital_wardrobe_agent` folder in VS Code.
3. Create the Git repository and push the contents of this folder to GitHub. Do not upload `.env`, `wardrobe.db`, or personal garment photos.
4. Sign in to Render and choose **New → Blueprint**.
5. Connect the GitHub repository and deploy the `render.yaml` configuration.
6. In the Render service's **Environment** settings, add:
   - `GEMINI_API_KEY`: your Gemini API key.
   - `FLASK_SECRET_KEY`: a long random secret if Render has not generated it from the Blueprint.
   - `ACCESS_PASSWORD`: a separate strong preview access code that you can share with the judges.
   - `GEMINI_MODEL`: keep `gemini-2.5-flash` unless you have verified another model is available to your API project.
7. Wait for the build and deployment to finish. Open the public `onrender.com` URL. The app will request the preview access code when `ACCESS_PASSWORD` is configured.

**Keep API keys in Render Environment settings. Never put them in HTML, JavaScript, GitHub, screenshots or the PPT.** If a key is accidentally committed, revoke it and generate a new one.

## Important deployment limitations

This ZIP is a hackathon MVP, not a production multi-customer SaaS release.

- The database currently represents one shared closet. The preview access code is a shared gate, not individual user accounts or data separation.
- A production launch needs user registration/login, per-user database ownership, CSRF protection, rate limiting, image/file validation and abuse controls.
- SQLite and uploaded images are stored on the app filesystem. Many entry-level hosting instances use ephemeral storage, so data can be lost on redeploy/restart. Before storing real users' wardrobes, move to a managed persistent database and object storage, and configure persistent backups.
- Check the hosting provider's current pricing, persistent-storage availability and service limits before launch.
- Gemini and background removal can incur usage, latency or hosting costs. Do not promise unlimited processing.
- Live weather is retrieved only when a city is provided and no manual weather text is entered. If the weather service is unavailable, the app asks the user to enter conditions manually.
- The planner is an in-app planner, not a Google or Apple calendar sync.

## Demo walkthrough

1. Open **My wardrobe** and add a garment using upload or camera.
2. Review the suggested details and edit them if needed.
3. Mark a garment as in laundry and confirm it is excluded from outfit suggestions.
4. Open **AI Stylist** or **Rewear Rescue** and choose an occasion.
5. Supply a city for live weather, or enter weather manually.
6. Review the generated options and approve one to save it.
7. Schedule the saved outfit in **Outfit planner**.
8. After actually wearing it, select **I wore this** to update wear history.
9. Review usage indicators in **Wardrobe insights**.

## Environment variables

See `.env.example`. At minimum, set a unique `FLASK_SECRET_KEY` for hosted production. `ACCESS_PASSWORD` enables a shared private-preview gate. Leave it unset only for a local development environment you control.
