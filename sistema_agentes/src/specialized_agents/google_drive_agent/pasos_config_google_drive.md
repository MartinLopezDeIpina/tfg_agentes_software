
- Create a new Google Cloud project
- Enable the Google Drive API
- Configure an OAuth consent screen ("internal" is fine for testing)
- Add OAuth scope https://www.googleapis.com/auth/drive.readonly
- Create an OAuth Client ID for application type "Desktop App"
- Download the JSON file of your client's OAuth keys
- Rename the key file to gcp-oauth.keys.json and place into the root of this repo (i.e. servers/gcp-oauth.keys.json):
GDRIVE_OAUTH_PATH=gcp-oauth.keys.json npx -y @modelcontextprotocol/server-gdrive auth -> autenticarse en navegador
- clonar el serv mcp, compilarlo con tsc y ejecutar con auth ->
GOOGLE_APPLICATION_CREDENTIALS="/home/martin/tfg_agentes_software/sistema_agentes/src/documentation_agent/gcp-oauth.keys.json" node dist/index.js auth
