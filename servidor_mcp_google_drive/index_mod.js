#!/usr/bin/env node
import { authenticate } from "@google-cloud/local-auth";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListResourcesRequestSchema, ListToolsRequestSchema, ReadResourceRequestSchema, ErrorCode, McpError, } from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import { google } from "googleapis";
import path from "path";

const drive = google.drive("v3");

const config = {
  specificFolderId: process.env.GDRIVE_FOLDER_ID || null
};

const server = new Server({
    name: "gdrive",
    version: "0.1.0",
}, {
    capabilities: {
        resources: {},
        tools: {},
    },
});

server.setRequestHandler(ListResourcesRequestSchema, async (request) => {
    const pageSize = 10;
    const params = {
        pageSize,
        fields: "nextPageToken, files(id, name, mimeType)",
    };

    // Añadir filtro por carpeta específica si está configurado
    if (config.specificFolderId) {
        params.q = `'${config.specificFolderId}' in parents`;
    }

    if (request.params?.cursor) {
        params.pageToken = request.params.cursor;
    }

    const res = await drive.files.list(params);
    const files = res.data.files;

    return {
        resources: files.map((file) => ({
            uri: `gdrive:///${file.id}`,
            mimeType: file.mimeType,
            name: file.name,
        })),
        nextCursor: res.data.nextPageToken,
    };
});

async function readFileContent(fileId) {
    // First get file metadata to check mime type
    const file = await drive.files.get({
        fileId,
        fields: "mimeType",
    });

    // For Google Docs/Sheets/etc we need to export
    if (file.data.mimeType?.startsWith("application/vnd.google-apps")) {
        let exportMimeType;
        switch (file.data.mimeType) {
            case "application/vnd.google-apps.document":
                exportMimeType = "text/markdown";
                break;
            case "application/vnd.google-apps.spreadsheet":
                exportMimeType = "text/csv";
                break;
            case "application/vnd.google-apps.presentation":
                exportMimeType = "text/plain";
                break;
            case "application/vnd.google-apps.drawing":
                exportMimeType = "image/png";
                break;
            default:
                exportMimeType = "text/plain";
        }
        const res = await drive.files.export({ fileId, mimeType: exportMimeType }, { responseType: "text" });
        return {
            mimeType: exportMimeType,
            content: res.data,
        };
    }

    // For regular files download content
    const res = await drive.files.get({ fileId, alt: "media" }, { responseType: "arraybuffer" });
    const mimeType = file.data.mimeType || "application/octet-stream";
    if (mimeType.startsWith("text/") || mimeType === "application/json") {
        return {
            mimeType: mimeType,
            content: Buffer.from(res.data).toString("utf-8"),
        };
    }
    else {
        return {
            mimeType: mimeType,
            content: Buffer.from(res.data).toString("base64"),
        };
    }
}

// Función recursiva para listar archivos y carpetas
async function listFilesRecursively(folderId, depth = 0, maxDepth = 5) {
    // Limitar la profundidad para evitar bucles infinitos o llamadas excesivas
    if (depth > maxDepth) return [];
    
    // Construir parámetros de consulta
    const params = {
        pageSize: 1000,
        fields: "files(id, name, mimeType, modifiedTime, size)"
    };
    
    // Solo añadir query si folderId es válido
    if (folderId) {
        params.q = `'${folderId}' in parents`;
    }
    
    // Consultar archivos en la carpeta actual usando params
    const res = await drive.files.list(params);
    
    let allFiles = [];
    
    // Procesar cada archivo/carpeta
    for (const file of res.data.files || []) {
        // Añadir este archivo/carpeta a nuestra lista
        allFiles.push({
            id: file.id,
            name: file.name,
            mimeType: file.mimeType,
            modifiedTime: file.modifiedTime,
            size: file.size || 'N/A',
            depth: depth
        });
        
        // Si es una carpeta, listar su contenido recursivamente
        if (file.mimeType === 'application/vnd.google-apps.folder') {
            const subFiles = await listFilesRecursively(file.id, depth + 1, maxDepth);
            allFiles = allFiles.concat(subFiles);
        }
    }
    
    return allFiles;
}

server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const fileId = request.params.uri.replace("gdrive:///", "");
    const result = await readFileContent(fileId);
    return {
        contents: [
            {
                uri: request.params.uri,
                mimeType: result.mimeType,
                text: result.content,
            },
        ],
    };
});

server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
        tools: [
            {
                name: "gdrive_search",
                description: "Search for files in google drive with a semantic query",
                inputSchema: {
                    type: "object",
                    properties: {
                        query: {
                            type: "string",
                            description: "Search query",
                        },
                    },
                    required: ["query"],
                },
            },
            {
                name: "gdrive_read_file",
                description: "Read a file from Google Drive using its Google Drive file ID",
                inputSchema: {
                    type: "object",
                    properties: {
                        file_id: {
                            type: "string",
                            description: "The ID of the file to read",
                        },
                    },
                    required: ["file_id"],
                },
            },
            {
                name: "gdrive_list_files",
                description: "List all files directories specified Google Drive directory",
                inputSchema: {
                    type: "object",
                    properties: {
                        page_size: {
                            type: "number",
                            description: "Number of files to return (default: 30, max: 100) - Only affects top-level pagination",
                        },
                        page_token: {
                            type: "string",
                            description: "Token for pagination if there are more files - Only affects top-level pagination",
                        }
                    },
                },
            },
            {
                name: "gdrive_list_files_json",
                description: "List all files in the specified Google Drive directory and return as JSON array of filenames",
                inputSchema: {
                    type: "object",
                    properties: {
                        page_size: {
                            type: "number",
                            description: "Number of files to return (default: 30, max: 100) - Only affects top-level pagination",
                        },
                        page_token: {
                            type: "string",
                            description: "Token for pagination if there are more files - Only affects top-level pagination",
                        }
                    },
                },
            }
        ],
    };
});

// Función para obtener solo subdirectorios recursivamente
async function getSubdirectoriesRecursively(folderId, depth = 0, maxDepth = 5) {
    if (depth > maxDepth) return [];

    // Consultar solo carpetas en el directorio actual
    const res = await drive.files.list({
        q: `'${folderId}' in parents and mimeType = 'application/vnd.google-apps.folder'`,
        pageSize: 1000,
        fields: "files(id, name, mimeType)"
    });

    let allFolders = [];

    // Procesar cada carpeta
    for (const folder of res.data.files || []) {
        // Añadir esta carpeta a nuestra lista
        allFolders.push({
            id: folder.id,
            name: folder.name
        });

        // Obtener subdirectorios recursivamente
        const subFolders = await getSubdirectoriesRecursively(folder.id, depth + 1, maxDepth);
        allFolders = allFolders.concat(subFolders);
    }

    return allFolders;
}

server.setRequestHandler(CallToolRequestSchema, async (request) => {
    if (request.params.name === "gdrive_search") {
        const userQuery = request.params.arguments?.query;
        const escapedQuery = userQuery.replace(/\\/g, "\\\\").replace(/'/g, "\\'");

        // Construir la consulta base
        let formattedQuery = `fullText contains '${escapedQuery}'`;
        
        // Si está configurado un directorio específico, incluir todos sus subdirectorios
        if (config.specificFolderId) {
            // Obtener solo los subdirectorios recursivamente (no los archivos)
            const subDirectories = await getSubdirectoriesRecursively(config.specificFolderId);
            
            // Añadir el directorio raíz e IDs de todos los subdirectorios
            const folderIds = [config.specificFolderId, ...subDirectories.map(folder => folder.id)];
            
            // Construir una consulta que incluya todas estas carpetas como posibles padres
            const parentsQuery = folderIds.map(id => `'${id}' in parents`).join(' or ');
            formattedQuery += ` and (${parentsQuery})`;
        }

        const res = await drive.files.list({
            q: formattedQuery,
            pageSize: 10,
            fields: "files(id, name, mimeType, modifiedTime, size)",
        });

        const fileList = res.data.files
            ?.map((file) => `${file.name} (${file.mimeType}) - ID: ${file.id}`)
            .join("\n");

        return {
            content: [
                {
                    type: "text",
                    text: `Found ${res.data.files?.length ?? 0} files${config.specificFolderId ? ' in the specified folder and its subdirectories' : ''}:\n${fileList}`,
                },
            ],
            isError: false,
        };
    }    
    else if (request.params.name === "gdrive_read_file") {
        const fileId = request.params.arguments?.file_id;
        if (!fileId) {
            throw new McpError(ErrorCode.InvalidParams, "File ID is required");
        }

        try {
            const result = await readFileContent(fileId);
            return {
                content: [
                    {
                        type: "text",
                        text: result.content,
                    },
                ],
                isError: false,
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: "text",
                        text: `Error reading file: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }
    else if (request.params.name === "gdrive_list_files") {
        try {
            // Determinar la carpeta raíz para iniciar el listado recursivo
            const rootFolderId = request.params.arguments?.folder_id || config.specificFolderId;
            
            // Usar la función recursiva para obtener todos los archivos
            const fileList = await listFilesRecursively(rootFolderId, 0, 5);
            
            // Creamos la respuesta con formato
            const folderInfo = config.specificFolderId
                ? `in folder ID: ${config.specificFolderId}`
                : 'in root or all folders';

            let response = `Found ${fileList.length} files recursively ${folderInfo}\n\n`;

            fileList.forEach((file, index) => {
                // Añadir indentación basada en la profundidad para visualizar la estructura
                const indent = '  '.repeat(file.depth);
                response += `${index + 1}. ${indent}${file.name}\n`;
                response += `   ${indent}ID: ${file.id}\n`;
                response += `   ${indent}Type: ${file.mimeType}\n`;
                response += `   ${indent}Modified: ${file.modifiedTime}\n`;
                response += `   ${indent}Size: ${file.size}\n\n`;
            });

            return {
                content: [
                    {
                        type: "text",
                        text: response,
                    },
                ],
                isError: false,
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: "text",
                        text: `Error listing files: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }

    else if (request.params.name === "gdrive_list_files_json") {

        try {
            // Determinar la carpeta raíz para iniciar el listado recursivo
            const rootFolderId = request.params.arguments?.folder_id || config.specificFolderId;

            // Usar la función recursiva para obtener todos los archivos
            const fileList = await listFilesRecursively(rootFolderId, 0, 5);

            // Crear un array de solo los nombres de archivos
            const file_json = fileList.map(file => ({name: file.name, url: `${file.id}/view`}));

            // Convertir a JSON string con formato
            const jsonResponse = JSON.stringify({ documents: file_json }, null, 2);

            return {
                content: [
                    {
                        type: "text",
                        text: jsonResponse,
                    },
                ],
                isError: false,
            };
        }
        catch (error) {
            return {
                content: [
                    {
                        type: "text",
                        text: `Error listing files: ${error.message}`,
                    },
                ],
                isError: true,
            };
        }
    }

    throw new Error("Tool not found");
});

const credentialsPath = process.env.MCP_GDRIVE_CREDENTIALS || path.join(process.cwd(), "credentials", ".gdrive-server-credentials.json");

async function authenticateAndSaveCredentials() {
    const keyPath = process.env.GOOGLE_APPLICATION_CREDENTIALS || path.join(process.cwd(), "credentials", "gcp-oauth.keys.json");
    console.log("Looking for keys at:", keyPath);
    console.log("Will save credentials to:", credentialsPath);

    const auth = await authenticate({
        keyfilePath: keyPath,
        scopes: ["https://www.googleapis.com/auth/drive.readonly"],
    });

    fs.writeFileSync(credentialsPath, JSON.stringify(auth.credentials));
    console.log("Credentials saved. You can now run the server.");
}

async function loadCredentialsAndRunServer() {
    if (!fs.existsSync(credentialsPath)) {
        console.error("Credentials not found. Please run with 'auth' argument first.");
        process.exit(1);
    }

    const credentials = JSON.parse(fs.readFileSync(credentialsPath, "utf-8"));
    const auth = new google.auth.OAuth2();
    auth.setCredentials(credentials);
    google.options({ auth });

    // Establecer el ID de carpeta desde la variable de entorno si está disponible
    if (process.env.GDRIVE_FOLDER_ID) {
        console.log(`Restricting operations to folder ID: ${process.env.GDRIVE_FOLDER_ID}`);
        config.specificFolderId = process.env.GDRIVE_FOLDER_ID;
    } else {
        console.log("No folder ID restriction set. Use the 'set_folder' tool or GDRIVE_FOLDER_ID environment variable to restrict operations to a specific folder.");
    }

    const transport = new StdioServerTransport();
    await server.connect(transport);
}

if (process.argv[2] === "auth") {
    authenticateAndSaveCredentials().catch(console.error);
}
else if (process.argv[2] === "folder" && process.argv[3]) {
    // Opción para especificar el ID de carpeta al iniciar
    config.specificFolderId = process.argv[3];
    console.log(`Setting folder ID to: ${process.argv[3]}`);
    loadCredentialsAndRunServer().catch((error) => {
        process.stderr.write(`Error: ${error}\n`);
        process.exit(1);
    });
}
else {
    loadCredentialsAndRunServer().catch((error) => {
        process.stderr.write(`Error: ${error}\n`);
        process.exit(1);
    });
}

async function debugReadFile(fileId) {
  try {
    console.log("Iniciando debug de gdrive_read_file...");
    console.log(`File ID a leer: ${fileId}`);

    // ✅ Simular exactamente la misma request que recibe el servidor
    const mockRequest = {
      params: {
        name: "gdrive_read_file",
        arguments: {
          file_id: fileId
        }
      }
    };

    console.log(`Request simulada:`, JSON.stringify(mockRequest, null, 2));

    try {
        const result = await readFileContent(fileId);
        const serverResponse = {
            content: [
                {
                    type: "text",
                    text: result.content,
                },
            ],
            isError: false,
        };
        
        console.log(`✅ Archivo leído exitosamente`);
        console.log(`   MIME Type: ${result.mimeType}`);
        console.log(`   Tamaño del contenido: ${result.content.length} caracteres`);
        console.log(`   Primeros 200 caracteres:`);
        console.log(`   "${result.content.substring(0, 200)}${result.content.length > 200 ? '...' : ''}"`);
        
        console.log("\n=== RESPUESTA DEL SERVIDOR ===");
        console.log(JSON.stringify(serverResponse, null, 2).substring(0, 500) + "...");
        
        return serverResponse;
    }
    catch (error) {
        const errorResponse = {
            content: [
                {
                    type: "text",
                    text: `Error reading file: ${error.message}`,
                },
            ],
            isError: true,
        };
        
        console.error(`❌ Error: ${error.message}`);
        console.log("\n=== RESPUESTA DE ERROR DEL SERVIDOR ===");
        console.log(JSON.stringify(errorResponse, null, 2));
        
        return errorResponse;
    }

    console.log("\n✅ Debug completado");
    
  } catch (error) {
    console.error("Error en debugReadFile:", error);
    console.error("Stack trace:", error.stack);
  }
}


async function debugListFiles() {
  try {
    console.log("Iniciando debug de gdrive_list_files...");
    console.log(`Config specificFolderId: ${config.specificFolderId}`);

    // ✅ Usar la función real en lugar de replicar la lógica
    const folder_id = '1axp3gAWo6VeAFq16oj1B5Nm06us2FBdR'
    const fileList = await listFilesRecursively(folder_id, 0, 5);

    console.log(`Se encontraron ${fileList.length} archivos recursivamente`);

    // Mostrar información detallada de cada archivo
    fileList.forEach((file, index) => {
      const indent = '  '.repeat(file.depth);
      console.log(`\nArchivo ${index + 1}: ${indent}${file.name}`);
      console.log(`  ${indent}ID: ${file.id}`);
      console.log(`  ${indent}Tipo: ${file.mimeType}`);
      console.log(`  ${indent}Profundidad: ${file.depth}`);
      console.log(`  ${indent}Modificado: ${file.modifiedTime}`);
      console.log(`  ${indent}Tamaño: ${file.size}`);
    });

    console.log("\nDebug completado con éxito");
    
    // También mostrar el formato que devuelve el servidor real
    console.log("\n=== SIMULANDO RESPUESTA DEL SERVIDOR ===");
    const folderInfo = config.specificFolderId
      ? `in folder ID: ${config.specificFolderId}`
      : 'in root or all folders';
    console.log(`Found ${fileList.length} files recursively ${folderInfo}`);
    
  } catch (error) {
    console.error("Error en debugListFiles:", error);
    console.error("Stack trace:", error.stack);
  }
}

// Modificación del bloque principal para incluir la opción de debug
if (process.argv[2] === "auth") {
  authenticateAndSaveCredentials().catch(console.error);
}
else if (process.argv[2] === "folder" && process.argv[3]) {
  // Opción para especificar el ID de carpeta al iniciar
  config.specificFolderId = process.argv[3];
  console.log(`Setting folder ID to: ${process.argv[3]}`);
  loadCredentialsAndRunServer().catch((error) => {
    process.stderr.write(`Error: ${error}\n`);
    process.exit(1);
  });
}
else if (process.argv[2] === "debug") {
  // Nueva opción para ejecutar el debug directamente
  (async () => {
    try {
      if (!fs.existsSync(credentialsPath)) {
        console.error("Credentials not found. Please run with 'auth' argument first.");
        process.exit(1);
      }

      const credentials = JSON.parse(fs.readFileSync(credentialsPath, "utf-8"));
      const auth = new google.auth.OAuth2();
      auth.setCredentials(credentials);
      google.options({ auth });

      // Establecer el ID de carpeta desde la variable de entorno si está disponible
      if (process.env.GDRIVE_FOLDER_ID) {
        console.log(`Restricting operations to folder ID: ${process.env.GDRIVE_FOLDER_ID}`);
        config.specificFolderId = process.env.GDRIVE_FOLDER_ID;
      }

      // Ejecutar la función de debug
      //await debugListFiles();
      await debugReadFile("1qzI7GibrlzU0tBo9ufGBQBXmCnrUdRYw")
      process.exit(0);
    } catch (error) {
      console.error("Error:", error);
      process.exit(1);
    }
  })();
}
else {
  loadCredentialsAndRunServer().catch((error) => {
    process.stderr.write(`Error: ${error}\n`);
    process.exit(1);
  });
}
