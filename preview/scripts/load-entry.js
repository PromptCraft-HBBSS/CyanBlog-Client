document.addEventListener("DOMContentLoaded", () => {
    const restoreScrollPosition = () => {
        const savedPosition = parseInt(localStorage.getItem("scrollPosition"));
        
        if (!isNaN(savedPosition)) {
            console.log(`Restoring scroll position: ${savedPosition}px`);
            window.scrollTo({
                top: savedPosition,
                behavior: "instant"
            });
        }
        
        // Clear saved position after restoration
        localStorage.removeItem("scrollPosition");
    };

    // Main content loading logic
    const loadContent = async () => {
        const docContent = document.getElementById("doc-content");
        const headline = document.getElementById("headline-content");
        const logline = document.getElementById("log-content");
        const dateline = document.getElementById("dateline-content");
        const pointer_res = await fetch("/pointer");
        const { pointer } = await pointer_res.json();
        logline.textContent = `pointer: ${pointer}`;

        try {
            const response = await fetch("/entry");

            if (!response.ok) {
                throw new Error("Python client is not running or no entry found |" + response.status);
            };

            const { data, title, dateline: entryDate, content } = await response.json();


            // Update UI with entry content
            console.log(title, entryDate, content);
            headline.textContent = title;
            dateline.textContent = entryDate;
            docContent.innerHTML = content;

            // Restore scroll position after content loads
            requestAnimationFrame(restoreScrollPosition);

        } catch (error) {
            console.error("Error fetching entry:", error.message);
            const status = error.message.split("|")[1].trim();
            if (status === "404") {
                headline.textContent = "No Entry Found";
                dateline.textContent = "No diary entry found for the current date.";
                docContent.textContent = "Please check back later.";
                restoreScrollPosition();
                return;
            } else if (status === "503") {
                headline.textContent = "Service Unavailable";
                dateline.textContent = "Python client is not running.";
                docContent.textContent = "Please try again later.";
                restoreScrollPosition();
                return;
            } else {
                headline.textContent = "Error";
                dateline.textContent = "Unable to load diary entry.";
                docContent.textContent = `Error: ${error.message}`;
                restoreScrollPosition();
            }
        }
    };

    // Scroll position tracking
    window.addEventListener("scroll", () => {
        localStorage.setItem("scrollPosition", window.scrollY.toString());
    });

    // Start loading content
    loadContent();
});

// SSE connection remains the same
const eventSource = new EventSource("/events");

eventSource.onmessage = (event) => {
    switch (event.data) {
        case "update":
            console.log("Diary entry changed, reloading...");
            location.reload();
            break;
        case "ping":
            console.log("Ping received from server");
            break;
        default:
            console.log("Unknown message received:", event.data);
    }
};

eventSource.onerror = (err) => {
    console.error("SSE connection error:", err);
};