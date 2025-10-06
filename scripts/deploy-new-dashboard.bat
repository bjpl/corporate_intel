@echo off
REM Deploy New Dashboard with Real Data Visualizations

echo.
echo ============================================================
echo   Deploying Updated Dashboard with Real Data Visualizations
echo ============================================================
echo.

REM Backup old dashboard
echo Backing up old dashboard...
if exist "src\visualization\dash_app.py" (
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
    for /f "tokens=1-2 delims=: " %%a in ('time /t') do (set mytime=%%a%%b)
    copy "src\visualization\dash_app.py" "src\visualization\dash_app_backup_%mydate%_%mytime%.py" >nul
    echo [OK] Backup created
) else (
    echo [WARNING] No existing dashboard found
)

REM Deploy new dashboard
echo.
echo Deploying new dashboard...
if exist "src\visualization\dash_app_updated.py" (
    copy /Y "src\visualization\dash_app_updated.py" "src\visualization\dash_app.py" >nul
    echo [OK] New dashboard deployed
) else (
    echo [ERROR] Updated dashboard file not found!
    exit /b 1
)

REM Show what changed
echo.
echo New Visualizations Added:
echo   1. [OK] Revenue Comparison Bar Chart (23 companies)
echo   2. [OK] Margin Comparison Chart (Gross vs Operating)
echo   3. [OK] Earnings Growth Distribution (12 companies with data)
echo   4. [OK] Revenue by Category Treemap
echo.
echo Removed Visualizations (No Data):
echo   - [X] Retention Curves (no cohort data)
echo   - [X] Cohort Heatmap (no cohort data)
echo   - [X] Competitive Landscape Scatter (insufficient YoY growth data)
echo.
echo Dashboard deployment complete!
echo.
echo To start the dashboard:
echo   python src\visualization\dash_app.py
echo.
echo Access at: http://localhost:8050
echo.
pause
