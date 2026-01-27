# fcucomposer Architect - Deployment & Operations Manual

This guide provides step-by-step instructions for deploying, configuring, and maintaining the fcucomposer Architect application on an Ubuntu server (specifically tailored for Nectar Research Cloud).

## 1. Nectar Cloud Configuration (Firewall)

**CRITICAL:** Before the app can be accessed from the internet, you must explicitly allow web traffic in the Nectar Dashboard. By default, Nectar blocks HTTPS (Port 443).

1.  Log in to the Nectar Dashboard.
2.  Navigate to **Network -> Security Groups**.
3.  Find the security group attached to your instance (usually named `http`, `default`, or one you created).
4.  Click **Manage Rules**.
5.  **Add HTTP Rule:**
    * Click `+ Add Rule`.
    * Rule: `HTTP (Port 80)`.
    * Remote: CIDR `0.0.0.0/0` (Allows traffic from anywhere).
    * Click `Add`.
6.  **Add HTTPS Rule (The missing link):**
    * Click `+ Add Rule`.
    * Rule: `HTTPS (Port 443)`.
    * Remote: CIDR `0.0.0.0/0`.
    * Click `Add`.

*If your browser "spins" or times out, this step is usually the cause.*

---

## 2. Initial Deployment

### Step A: Transfer Code to Server
If you haven't already, upload your project files to the server.

```bash
# From your local machine
scp -r /path/to/fcucomposer user@your-server-ip:/home/ubuntu/
```

### Step B: Run the Setup Script
SSH into your server and execute the automated deployment script. You must provide your `GOOGLE_API_KEY` here so it can be saved into the system service.

```bash
cd fcucomposer

# Make the script executable
chmod +x deploy/setup.sh

# Run with sudo, passing the API key environment variable
export GOOGLE_API_KEY="your_actual_gemini_api_key_here"
sudo -E ./deploy/setup.sh
```

**What this script does:**
* Installs system dependencies (Python, Node.js, Nginx).
* Creates a Python virtual environment (`venv`) and installs dependencies.
* Builds the React frontend (`npm run build`).
* Configures Nginx as a Reverse Proxy (Port 443 -> 8997).
* Generates a Self-Signed SSL Certificate.
* Sets up a Systemd Service (`fcucomposer.service`) to keep the backend running.

---

## 3. Maintenance: How to Update Code

When you make changes to the code (frontend or backend), follow these specific routines.

### Scenario A: Backend Changes (Python)
If you modified files in `src/backend/`:

1.  Pull the latest code:
    ```bash
    git pull
    ```
2.  Restart the Backend Service:
    ```bash
    sudo systemctl restart fcucomposer
    ```
3.  Verify it's running:
    ```bash
    sudo systemctl status fcucomposer
    ```

### Scenario B: Frontend Changes (React/TypeScript)
If you modified files in `src/frontend/`:

1.  Pull the latest code:
    ```bash
    git pull
    ```
2.  Rebuild the Frontend:
    ```bash
    cd src/frontend
    npm install       # Only needed if you added new packages
    npm run build
    ```
3.  Deploy the new build:
    ```bash
    # Copy the new 'dist' folder to the web root
    sudo cp -r dist/* /var/www/fcucomposer/
    ```
    *(No restart required; Nginx serves the new files immediately).*

### Scenario C: Dependency Changes
If you added new Python libraries to `requirements.txt`:

```bash
source venv/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart fcucomposer
```

---

## 4. Troubleshooting

### App is "Spinning" / Timeout
* **Cause:** Firewall blocking connection.
* **Fix:** Check **Step 1** (Nectar Security Groups). Verify `nc -zv YOUR_IP 443` from your local machine returns "succeeded".

### "Connection Refused" / "502 Bad Gateway"
* **Cause:** The Python backend is crashed or stopped.
* **Fix:** Check the logs to see the error.
    ```bash
    sudo journalctl -u fcucomposer -n 50 --no-pager
    ```

### "API Key Missing" Error in App
* **Cause:** The API key wasn't correctly written to the service file or is invalid.
* **Fix:**
    1.  Edit the service file: `sudo nano /etc/systemd/system/fcucomposer.service`
    2.  Check the line: `Environment="GOOGLE_API_KEY=..."`
    3.  Save, then run:
        ```bash
        sudo systemctl daemon-reload
        sudo systemctl restart fcucomposer
        ```

### Browser Certificate Warning
* **Cause:** Self-signed certificates are not trusted by browsers automatically.
* **Fix:** Click "Advanced" -> "Proceed to <ip> (unsafe)". For a real certificate, you need a domain name and Let's Encrypt (certbot).