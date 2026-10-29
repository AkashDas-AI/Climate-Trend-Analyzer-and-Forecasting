# Contributing to Climate Trend Analyzer

Welcome to the **Climate Trend Analyzer** project. We appreciate contributions from the scientific and open-source communities.

**Project Author**: Akash Das

---

## 1. Project-Local Environment Setup

To guarantee reproducibility and avoid global pollution, all development must take place within a dedicated project-local virtual environment located at `.venv/` inside the project root.

### Creating the Virtual Environment
From the project root directory:

```bash
# Windows / macOS / Linux
python -m venv .venv
```

### Activating the Environment

- **Windows PowerShell**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **Windows Command Prompt (cmd)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **macOS / Linux**:
  ```bash
  source .venv/bin/activate
  ```

### Verifying the Interpreter
Verify that `python` and `pip` resolve strictly inside `.venv`:
```powershell
# Windows
Get-Command python
python -c "import sys; print(sys.executable)"

# Unix / macOS
which python
python -c "import sys; print(sys.executable)"
```

### Installing Dependencies
Always use `python -m pip` within the activated environment:
```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -e .
```

---

## 2. Hygiene & Confidentiality Rules

> [!WARNING]
> **Strict Git Hygiene:**
> - **NEVER** commit `.venv/` or any other virtual environment folders.
> - **NEVER** commit secrets, API keys, or `.env` files (use `.env.example` as a template).
> - **NEVER** commit unapproved external raw datasets or massive binary model checkpoints. Keep raw observations in `data/raw/` and generated outputs in `outputs/` (both are git-ignored by default except `.gitkeep`).

---

## 3. Running the Test Suite

Always execute tests using the project's `.venv` interpreter:

```bash
python -m pytest -v
```

Before submitting a pull request:
- All unit tests must pass (`pytest tests/`).
- Code must follow PEP 8 standards.
- Type annotations and docstrings should accompany all new public functions and classes.

---

## 4. Git Workflow & Submissions

1. Fork or branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Verify git status before staging changes:
   ```bash
   git status
   ```
3. Commit with concise, descriptive commit messages:
   ```bash
   git commit -m "feat(transform): add decadal smoothing support"
   ```
4. Push and open a Pull Request describing your changes, methodology, and verification steps.

