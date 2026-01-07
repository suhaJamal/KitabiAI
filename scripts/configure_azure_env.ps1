# PowerShell script to configure Azure App Service environment variables
# Run this if you have Azure CLI installed

# Configuration
$APP_NAME = "kitabiai-app"
$RESOURCE_GROUP = "bookautomation-insights"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Azure App Service Configuration Script" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This will add environment variables to: $APP_NAME"
Write-Host "Resource Group: $RESOURCE_GROUP"
Write-Host ""

# Check if Azure CLI is installed
try {
    $azVersion = az version 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI not found"
    }
} catch {
    Write-Host "❌ Azure CLI not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Azure CLI first:"
    Write-Host "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows"
    Write-Host ""
    Write-Host "Or configure manually via Azure Portal (see AZURE_DEPLOYMENT_GUIDE.md)"
    exit 1
}

# Check if logged in
Write-Host "Checking Azure login status..."
try {
    $account = az account show 2>$null | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0) {
        throw "Not logged in"
    }
} catch {
    Write-Host "❌ Not logged in to Azure" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run: az login"
    exit 1
}

Write-Host "✅ Logged in to Azure" -ForegroundColor Green
Write-Host ""

# Show current subscription
$subscription = $account.name
Write-Host "Current subscription: $subscription"
Write-Host ""

# Confirm before proceeding
$confirm = Read-Host "Do you want to proceed? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "❌ Cancelled" -ForegroundColor Red
    exit 0
}

Write-Host ""
Write-Host "Adding environment variables..." -ForegroundColor Yellow
Write-Host ""

# Add container name settings
az webapp config appsettings set `
  --name $APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --settings `
    AZURE_STORAGE_CONTAINER_HTML="books-html" `
    AZURE_STORAGE_CONTAINER_MARKDOWN="books-markdown" `
    AZURE_STORAGE_CONTAINER_JSON="books-json" `
    AZURE_STORAGE_CONTAINER_PDF="books-pdf" `
    AZURE_STORAGE_CONTAINER_IMAGES="books-images" `
  --output table

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ Configuration Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The app will restart automatically (takes ~30 seconds)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Wait for app to restart"
Write-Host "2. Deploy your code: git push origin main"
Write-Host "3. Test at: https://$APP_NAME.azurewebsites.net"
Write-Host ""
