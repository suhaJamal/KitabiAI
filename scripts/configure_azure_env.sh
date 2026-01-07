#!/bin/bash
# Script to configure Azure App Service environment variables
# Run this if you have Azure CLI installed

# Configuration
APP_NAME="kitabiai-app"
RESOURCE_GROUP="bookautomation-insights"

echo "============================================================"
echo "Azure App Service Configuration Script"
echo "============================================================"
echo ""
echo "This will add environment variables to: $APP_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found!"
    echo ""
    echo "Please install Azure CLI first:"
    echo "https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    echo ""
    echo "Or configure manually via Azure Portal (see AZURE_DEPLOYMENT_GUIDE.md)"
    exit 1
fi

# Check if logged in
echo "Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure"
    echo ""
    echo "Please run: az login"
    exit 1
fi

echo "✅ Logged in to Azure"
echo ""

# Show current subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "Current subscription: $SUBSCRIPTION"
echo ""

# Confirm before proceeding
read -p "Do you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "❌ Cancelled"
    exit 0
fi

echo ""
echo "Adding environment variables..."
echo ""

# Add container name settings
az webapp config appsettings set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --settings \
    AZURE_STORAGE_CONTAINER_HTML="books-html" \
    AZURE_STORAGE_CONTAINER_MARKDOWN="books-markdown" \
    AZURE_STORAGE_CONTAINER_JSON="books-json" \
    AZURE_STORAGE_CONTAINER_PDF="books-pdf" \
    AZURE_STORAGE_CONTAINER_IMAGES="books-images" \
  --output table

echo ""
echo "============================================================"
echo "✅ Configuration Complete!"
echo "============================================================"
echo ""
echo "The app will restart automatically (takes ~30 seconds)"
echo ""
echo "Next steps:"
echo "1. Wait for app to restart"
echo "2. Deploy your code: git push origin main"
echo "3. Test at: https://${APP_NAME}.azurewebsites.net"
echo ""
