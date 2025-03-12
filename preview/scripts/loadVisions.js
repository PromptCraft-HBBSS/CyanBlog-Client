// Func to load entries

async function load() {
    // Fetching logic here
    try {
        // Fetch res
        const res = await fetch('/req-visions');
        if (!res.ok) {
            throw new Error('response not okay'); // Handle req err
        }
        
        const { title, dateline, content } = await res.json(); // Extract body

        // Injection
        document.getElementById('headline-content').textContent = title;
        document.getElementById('dateline-content').textContent = dateline;
        document.getElementById('doc-content').innerHTML = content;

    } catch (err) {
        document.getElementById('headline-content').textContent = 'Error'
        document.getElementById('doc-content').textContent = err.message;
    }
}

load();