const express = require("express");
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const matter = require("gray-matter");

const app = express();
const PORT = 8001;
const docsDir = path.join(__dirname, "/../docs");

let currentFilename = null;
let lastUpdated = null;
let clients = []; // Array to hold connected clients for SSE

app.use(express.json());
app.use(express.static(__dirname));
app.use('/docs', express.static(docsDir));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, "index.html"));
});

// API: Python client registers the filename
app.post("/register-filename", (req, res) => {
    console.log('test');
    const { filename } = req.body;
    if (!filename) {
        return res.status(400).json({ error: "Filename is required" });
    }
    currentFilename = filename;
    lastUpdated = Date.now();
    console.log(`Registered filename: ${filename}`);
    watchFile();  // Start watching the file once it's registered
    res.json({ message: "Filename registered successfully" });
});

app.get('/pointer', (req, res) => {
    res.json({ pointer: currentFilename });
})

// API: Get diary entry based on registered filename
app.get("/entry", (req, res) => {
    if (!currentFilename || Date.now() - lastUpdated > 30000) {  // Timeout after 30s
        return res.status(503).send("<h1>Error: Python client is not running</h1>");
    }

    const filePath = path.join(docsDir, currentFilename, "entry.md");
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            console.error('Error reading file:', err);
            return res.status(404).json({ error: 'Entry not found.' });
        }
        try {
            const { data: frontmatter, content } = matter(data);
            const title = frontmatter.title || `Diary @ ${currentFilename}`;
            const dateline = currentFilename;

            console.log('Markdown content:', content);
            const htmlContent = marked(content);
            console.log('Markdown content:', htmlContent);

            const body = {
                data,
                title,
                dateline,
                content: htmlContent,
                ...frontmatter
            };

            console.log('Entry:', body);
            res.json(body);
        } catch (err) {
            console.error('Error processing markdown:', err);
            return res.status(500).json({ error: 'Error processing markdown content.' });
        }
    });
});

// SSE Endpoint: Listen for file changes
app.get("/events", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");

    clients.push(res);
    console.log("Client connected to SSE");

    // Remove client from the list when the connection is closed
    req.on("close", () => {
        clients = clients.filter(client => client !== res);
        console.log("Client disconnected from SSE");
    });
});

app.post("/client-event", (req, res) => {
    console.log("Client event received:", req.body);
    const { event } = req.body;
    clients.forEach(client => client.write(`data: ${event}\n\n`));
    return res.status(200).json({ message: "Client event received" });
})

app.post("/refresh", (req, res) => {
    clients.forEach(client => client.write("data: update\n\n"));
    console.log("Refresh sent to all clients");
    return res.status(200).json({ message: "Refresh sent to all clients" });
});

// Watch the file for changes and notify connected clients
function watchFile() {
    if (!currentFilename) return

    const filePath = path.join(docsDir, currentFilename, "entry.md");
    if (!fs.existsSync(filePath)) return;

    console.log(`Started watching file: ${filePath}`);
    fs.watchFile(filePath, { interval: 1000 }, () => {
        console.log(`File ${filePath} changed, notifying clients...`);
        // Notify all connected clients about the update
        clients.forEach(client => client.write("data: update\n\n"));
    });
}

// Periodically check if a file is registered and watch it
// Removed the setInterval because watchFile is now triggered after filename registration
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}/`);
});
