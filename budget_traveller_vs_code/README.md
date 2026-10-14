# Budget Traveller with Coupons

## Run in VS Code (Windows)

1. Install Python 3.10+ and open this folder in VS Code.
2. Open Terminal > New Terminal.
3. Create a virtual environment (recommended):
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```powershell
   python -m streamlit run app.py
   ```
6. Open the local URL shown in the terminal (usually http://localhost:8501).

CSV upload expects a header row named `u,v,p`, e.g.
```csv
u,v,p
1,2,100
2,3,200
3,5,400
```
