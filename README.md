# 🦞 Run OpenClaw with Ollama on Phone (Android/Termux)

Run a powerful, local AI agent on your Android device for free using Termux, Ollama, and OpenClaw.

---
<p align="center">
  <img src="ollama-with-openclaw.jpeg" width="95%" />
</p>
---

## 📋 Prerequisites

**Note:** If you haven't installed OpenClaw before, please watch this video first:  
https://youtu.be/1pLPBgseffo?si=O_q3-8MvEsv7u28l

Before starting, ensure you have the following installed on your Android device:
- **Termux** (Recommended version from F-Droid or GitHub)
- **Node.js** (Required for OpenClaw)

> **Important:** Run the commands from this repository up to the network setup commands before proceeding with the Ollama setup.  
> Repository: https://github.com/AbuZar-Ansarii/Clawbot.git

## 🚀 Installation & Setup with Ollama

Follow these steps in order to get your local environment running.

### 1. Install and Start Ollama

Open Termux and run the following command to install the Ollama package:

```bash
pkg install ollama
```

Start the Ollama server:

```bash
ollama serve
```

> **Note:** Keep this session running. You will need to open a new Termux session for the following steps.

### 2. Download the Model

In a new Termux session, pull the desired model. For example:

```bash
ollama pull glm-5:cloud
```

Run the model:

```bash
ollama run glm-5:cloud
```

### 3. Install OpenClaw

Install the OpenClaw CLI globally using npm:

```bash
npm install -g openclaw@latest
```

## 🛠️ Configuration

Run the onboarding wizard to configure your environment and install the background daemon:

```bash
openclaw onboard --install-daemon
```

## ⚡ Usage

Once configured, you can launch OpenClaw using the following commands:

**Launch with Configuration Menu:**

```bash
ollama launch openclaw --config
```

**OpenClaw Dashboard URL:**

```
http://127.0.0.1:18789
```

## 💡 Troubleshooting

- **Memory Issues:** Running LLMs on mobile can be resource-intensive. Ensure you have at least 4GB of free RAM.
- **Stay Awake:** Use the `termux-wake-lock` command to prevent Android from killing the process when the screen is off.

## ✅ Testing

You can validate that the README still includes the required setup instructions by running:

```bash
make test
```

This runs a smoke test script (`tests_readme.sh`) used by CI.
