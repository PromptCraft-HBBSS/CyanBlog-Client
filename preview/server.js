const express = require("express");
const fs = require("fs");
const path = require("path");
const { marked } = require("marked");
const matter = require("gray-matter");

const app = express();
const PORT = 8001;
const docsDir = path.join(__dirname, "/../docs");

let currentFilename = null;
let lastHeartbeat = null;
let clients = [];
let fileWatcher = null;
const HEARTBEAT_TIMEOUT = 30000; // 30s timeout

app.use(express.json());
app.use(express.static(__dirname));
app.use("/docs", express.static(docsDir));

app.get("/", (req, res) => {
    res.sendFile(path.join(__dirname, "index.html"));
});

// Register filename from Python client
app.post("/register-filename", (req, res) => {
    const { filename } = req.body;
    if (!filename) {
        return res.status(400).json({ error: "Filename is required" });
    }

    currentFilename = filename;
    lastHeartbeat = Date.now();
    console.log(`Registered filename: ${filename}`);

    res.json({ message: "Filename registered successfully" });
});

// Get the current filename pointer
app.get("/pointer", (req, res) => {
    res.json({ pointer: currentFilename });
});

// Get diary entry based on registered filename
app.get("/entry", (req, res) => {
    if (!currentFilename || Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
        return res.status(503).send("<h1>Error: Python client is not running</h1>");
    }

    const filePath = path.join(docsDir, currentFilename, "entry.md");
    fs.readFile(filePath, "utf8", (err, data) => {
        if (err) {
            console.error("Error reading file:", err);
            return res.status(404).json({ error: "Entry not found." });
        }
        try {
            const { data: frontmatter, content } = matter(data);
            const title = frontmatter.title || `Diary @ ${currentFilename}`;
            const dateline = currentFilename;

            const htmlContent = marked(content);

            const body = {
                data,
                title,
                dateline,
                content: htmlContent,
                ...frontmatter,
            };

            res.json(body);
        } catch (err) {
            console.error("Error processing markdown:", err);
            return res.status(500).json({ error: "Error processing markdown content." });
        }
    });
});

// Receive heartbeat from Python client
app.post("/heartbeat", (req, res) => {
    if (!currentFilename) {
        return res.status(400).json({ error: "No filename registered" });
    }

    lastHeartbeat = Date.now();
    console.log("Heartbeat received");

    // Start file watching if not already started
    if (!fileWatcher) {
        startWatchingFile();
    }

    res.json({ message: "Heartbeat received" });
});

// SSE Endpoint: Listen for file changes
app.get("/events", (req, res) => {
    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");

    clients.push(res);
    console.log("Client connected to SSE");

    req.on("close", () => {
        clients = clients.filter(client => client !== res);
        console.log("Client disconnected from SSE");
    });
});

// Client-triggered refresh
app.post("/refresh", (req, res) => {
    clients.forEach(client => client.write("data: update\n\n"));
    console.log("Refresh sent to all clients");
    res.status(200).json({ message: "Refresh sent to all clients" });
});

// Notify clients of file changes
function notifyClients() {
    clients.forEach(client => client.write("data: update\n\n"));
}

// Start watching file for changes
function startWatchingFile() {
    if (!currentFilename) return;

    const filePath = path.join(docsDir, currentFilename, "entry.md");
    if (!fs.existsSync(filePath)) return;

    console.log(`Started watching file: ${filePath}`);

    fileWatcher = fs.watchFile(filePath, { interval: 1000 }, () => {
        console.log(`File ${filePath} changed, notifying clients...`);
        notifyClients();
    });
}

// Check if heartbeat is lost
setInterval(() => {
    if (currentFilename && Date.now() - lastHeartbeat > HEARTBEAT_TIMEOUT) {
        console.log("Python client inactive. Stopping file watching...");
        currentFilename = null;
        lastHeartbeat = null;
        if (fileWatcher) {
            fs.unwatchFile(path.join(docsDir, currentFilename, "entry.md"));
            fileWatcher = null;
        }
    }
}, 5000);

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}/`);
});
